import {CreateMLCEngine} from "@mlc-ai/web-llm";
import {Streamlit} from "streamlit-component-lib";

let activeRequest;
async function reply(request) {
  const status = document.querySelector("#status");
  try {
    const adapter = await navigator.gpu?.requestAdapter();
    if (!adapter) throw new Error("No compatible graphics adapter");
    const precision = adapter.features.has("shader-f16") ? "f16" : "f32";
    const engine = await CreateMLCEngine(`SmolLM2-360M-Instruct-q4${precision}_1-MLC`, {
      initProgressCallback: progress => {
        status.textContent = `Preparing Reco · ${Math.round(progress.progress * 100)}%`;
      }
    });
    const response = await engine.chat.completions.create({
      messages: request.messages, temperature: 0, max_tokens: 180,
      response_format: {type: "json_object", schema: JSON.stringify(request.schema)}
    });
    const {kind, reply, ids} = JSON.parse(response.choices[0].message.content);
    Streamlit.setComponentValue({id: request.id, kind, reply, ids});
  } catch {
    Streamlit.setComponentValue({id: request.id, unavailable: true});
  }
}
Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, event => {
  const request = event.detail.args;
  if (request.id !== activeRequest) {
    activeRequest = request.id;
    reply(request);
  }
  Streamlit.setFrameHeight(44);
});
Streamlit.setComponentReady();
