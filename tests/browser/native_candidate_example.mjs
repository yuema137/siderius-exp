/** Real exported task source -> GUI edit/accept/save -> native offline preparation.
 * Requires EDITOR_PYTHON, CONSOLE_EXAMPLE_CONFIG, CONSOLE_PLAYWRIGHT_MODULE,
 * CONSOLE_BROWSER_EXECUTABLE, CONSOLE_EVIDENCE_DIR. Never presses candidate Launch.
 */
import assert from 'node:assert/strict';
import {spawn, execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {mkdir, readFile, stat, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
for (const name of ['EDITOR_PYTHON', 'CONSOLE_EXAMPLE_CONFIG', 'CONSOLE_PLAYWRIGHT_MODULE', 'CONSOLE_BROWSER_EXECUTABLE', 'CONSOLE_EVIDENCE_DIR']) assert.ok(process.env[name], `Set ${name}`);
const python = process.env.EDITOR_PYTHON, evidence = resolve(process.env.CONSOLE_EVIDENCE_DIR);
const configPath = resolve(process.env.CONSOLE_EXAMPLE_CONFIG), config = JSON.parse(await readFile(configPath, 'utf8'));
const project = config.editor_projects[0], task = config.tasks[0];
await mkdir(evidence, {recursive: true});
const native = (command, input) => execFileSync(python, ['-m', 'workflows.definition', command, '--input', input], {encoding: 'utf8'});
const exported = JSON.parse(native('to-json', project.source_file));
exported.preparation_options.proposal_advice = 'Code-side explicit small baseline';
await writeFile(resolve(evidence, 'code-export.json'), JSON.stringify(exported));
const codeSource = native('to-python', resolve(evidence, 'code-export.json'));
await writeFile(project.source_file, codeSource);
const server = spawn(python, ['-m', 'tools.candidate_console', 'serve', '--config', configPath], {stdio: ['ignore', 'pipe', 'pipe']});
let browser, page, stderr = '';
server.stderr.on('data', data => {stderr += data;});
const calls = [], responses = [], faults = [];
const timer = setTimeout(() => {server.kill('SIGTERM'); console.error('Exported candidate browser witness timed out'); process.exit(2);}, 120000);
try {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error(`Console exited: ${stderr}`);
    try {if ((await fetch(config.browser_origin)).ok) break;} catch (_) {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  const {chromium} = createRequire(import.meta.url)(process.env.CONSOLE_PLAYWRIGHT_MODULE);
  browser = await chromium.launch({headless: true, executablePath: process.env.CONSOLE_BROWSER_EXECUTABLE});
  page = await browser.newPage();
  page.on('pageerror', error => faults.push(error.message));
  page.on('request', request => {const path = new URL(request.url()).pathname; if (path.startsWith('/api/')) calls.push({method: request.method(), path});});
  page.on('response', response => {const path = new URL(response.url()).pathname; if (path.startsWith('/api/')) responses.push({status: response.status(), path});});
  await page.goto(`${config.browser_origin}/#workflow`);
  await page.locator('#token').fill((await readFile(config.auth_token_file, 'utf8')).trim());
  await page.locator('#access-form button').click();
  await page.locator('#access-status').filter({hasText: 'Connected.'}).waitFor();
  await page.waitForFunction(expected => document.getElementById('editor-source').value === expected, codeSource);
  assert.equal(await page.locator('#editor-project').inputValue(), project.project_id);
  await page.locator('#editor-advanced').evaluate(el => {el.open = true;});
  const guiSource = codeSource.replace('Code-side explicit small baseline', 'GUI-side explicit small baseline');
  assert.notEqual(guiSource, codeSource);
  await page.locator('#editor-source').fill(guiSource);
  await page.locator('#editor-task-choice').selectOption(task.task_id);
  const reviewedResponse = page.waitForResponse(response => new URL(response.url()).pathname === `/api/editor/${project.project_id}/review`);
  await page.locator('#editor-review').click();
  const reviewedHttp = await reviewedResponse;
  assert.equal(reviewedHttp.status(), 200);
  const reviewed = await reviewedHttp.json();
  assert.equal(reviewed.task_reference_update.save_supported, true);
  assert.equal(reviewed.document.task_binding.semantic_fingerprint, task.task_revision.semantic_fingerprint);
  assert.equal(await page.locator('#editor-save').isDisabled(), true);
  await page.locator('#editor-task-acknowledge').check();
  if (await page.locator('#editor-task-adopt').count()) await page.locator('#editor-task-adopt').check();
  const savedResponse = page.waitForResponse(response => new URL(response.url()).pathname === `/api/editor/${project.project_id}/save`);
  await page.locator('#editor-save').click();
  const savedHttp = await savedResponse;
  assert.equal(savedHttp.status(), 200);
  const saved = await savedHttp.json();
  await page.locator('#editor-status').filter({hasText: 'Saved reviewed bytes'}).waitFor();
  const source = await readFile(project.source_file, 'utf8');
  assert.equal(source, reviewed.source);
  const roundtrip = JSON.parse(native('to-json', project.source_file));
  assert.equal(roundtrip.preparation_options.proposal_advice, 'GUI-side explicit small baseline');
  assert.deepEqual(roundtrip.task_binding, exported.task_binding);
  assert.deepEqual(roundtrip.definition.nodes, exported.definition.nodes);
  await page.locator('#new-run-task').selectOption(task.task_id);
  await page.locator('#new-run-name').fill(`${project.project_id}_gui_candidate_001`);
  const preparationReviewResponse = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/reusable-preparations/review'));
  await page.locator('#new-run-review').click();
  const preparationHttp = await preparationReviewResponse;
  assert.equal(preparationHttp.status(), 200);
  const preparation = await preparationHttp.json();
  assert.equal(preparation.source_path, project.source_file);
  assert.equal(preparation.selection.expected_source_sha256, saved.sha256);
  const preparedResponse = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/reusable-preparations/prepare'));
  await page.locator('#new-run-prepare').click();
  assert.equal((await preparedResponse).status(), 202);
  let status;
  for (let attempt = 0; attempt < 130; attempt++) {
    status = await page.evaluate(id => window.consoleSession.request('operations/' + id), preparation.selection.preparation_operation_id);
    if (status.state === 'completed' || status.state === 'operation_failed') break;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  assert.equal(status.native_status, 'prepared', JSON.stringify(status));
  assert.equal(status.operation_id, preparation.selection.preparation_operation_id);
  assert.equal(await readFile(resolve(dirname(preparation.inputs), 'workflow.py.snapshot'), 'utf8'), source);
  await assert.rejects(stat(preparation.workspace), {code: 'ENOENT'});
  await page.locator('#new-run-check').click();
  await page.locator('#new-run-open').click();
  const captureResponse = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/reusable-captures/review'));
  await page.locator('#capture-review').click();
  const captureHttp = await captureResponse;
  assert.equal(captureHttp.status(), 200);
  const capture = await captureHttp.json();
  assert.equal(capture.credential_readiness.file_status, 'readable');
  assert.deepEqual(capture.credential_readiness.missing_names, ['OPENAI_API_KEY']);
  assert.equal(capture.credential_readiness.ready, false);
  await page.locator('#capture-status').filter({hasText: 'Capture reviewed.'}).waitFor();
  assert.match(await page.locator('#capture-details').textContent(), /OPENAI_API_KEY/);
  assert.equal(await page.locator('#capture-launch').isDisabled(), true);
  assert.equal(await page.evaluate(() => window.consoleSession.connected), true);
  assert.ok(calls.every(call => !call.path.endsWith('/launch')), 'Candidate launch is forbidden in this offline witness');
  assert.deepEqual(faults, []);
  await page.screenshot({path: resolve(evidence, `${project.project_id}-candidate.png`), fullPage: true});
  await writeFile(resolve(evidence, 'receipt.json'), JSON.stringify({framework_python: python, framework_revision: execFileSync('git', ['-C', resolve(dirname(python), '../..'), 'rev-parse', 'HEAD'], {encoding: 'utf8'}).trim(), task_binding: task.task_revision, source_path: project.source_file, saved_source_sha256: saved.sha256, preparation: {operation_id: status.operation_id, state: status.state, native_status: status.native_status, source_path: preparation.source_path, inputs: preparation.inputs}, credential_readiness: capture.credential_readiness, connected: true, candidate_launched: false, calls, responses, faults}, null, 2));
  console.log('PASS: exported task source -> actual GUI review/accept/save -> native offline preparation; no candidate launch.');
} catch (error) {
  if (page) await page.screenshot({path: resolve(evidence, 'failure.png'), fullPage: true});
  await writeFile(resolve(evidence, 'failure.json'), JSON.stringify({error: error.message, calls, responses, faults, server_error: stderr}, null, 2));
  throw error;
} finally {
  clearTimeout(timer);
  if (browser) await browser.close();
  if (server.exitCode === null) {const done = new Promise(resolve => server.once('exit', resolve)); server.kill('SIGTERM'); await done;}
}
