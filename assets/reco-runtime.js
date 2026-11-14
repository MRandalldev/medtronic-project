// Both the launcher and the conversation live in the same page. Only model weights
// and the engine are shared. Each inference receives its own account-scoped prompt.
export default function ({data, setTriggerValue, parentElement}) {
  const root = parentElement.querySelector('span');
  const runtime = window.__recoRuntime ??= {};
  function start() {
    if (!runtime.ready) {
      runtime.ready = import(new URL(data.url, window.location.origin).href).then(async module => {
        await module.prepare();
        return module;
      });
      runtime.ready.catch(() => {});
    }
    return runtime.ready;
  }
  if (!data.request) {
    if (!runtime.ready && !runtime.scheduled) {
      runtime.scheduled = true;
      (window.requestIdleCallback || (cb => setTimeout(cb, 100)))(start, {timeout:1300});
    }
    return;
  }
  const request = data.request;
  if (root.dataset.request === request.id) return;
  root.dataset.request = request.id;
  async function run() {
    // Serve the offline reply promptly during a first-time model download.
    let timer, deadline;
    try {
      const module = await Promise.race([start(), new Promise((_,reject) => {
        timer = setTimeout(() => reject(new Error("Cold model")), 3500);
      })]);
      const result = await Promise.race([module.respond(request.messages, request.schema, request.dialogue), new Promise((_,reject) => { deadline = setTimeout(() => reject(new Error("Response timeout")), 25000); })]);
      if (root.isConnected && root.dataset.request === request.id) setTriggerValue('answer', {...result,id:request.id});
    } catch {
      if (root.isConnected && root.dataset.request === request.id) setTriggerValue('answer',{id:request.id,unavailable:true});
    } finally { clearTimeout(timer); clearTimeout(deadline); }
  }
  run();
}
