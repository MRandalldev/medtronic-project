import {CreateMLCEngine, prebuiltAppConfig} from "@mlc-ai/web-llm";
import {Streamlit} from "streamlit-component-lib";
const button=document.querySelector("#start"), status=document.querySelector("#status");
let args,engine;
function show(message){status.textContent=message; Streamlit.setFrameHeight();}
Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, event=>{
  args=event.detail.args; Streamlit.setFrameHeight();
});
button.onclick=async ()=>{
  const request=args;
  button.disabled=true;
  try{
    if(!navigator.gpu) throw new Error("WebGPU is unavailable. Choose Source lookup or Ollama.");
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) throw new Error("No WebGPU adapter is available. Choose another engine.");
    const precision = adapter.features.has("shader-f16") ? "f16" : "f32";
    const model = prebuiltAppConfig.model_list.find(m =>
      m.model_id === `SmolLM2-360M-Instruct-q4${precision}_1-MLC`
    )?.model_id;
    if(!model) throw new Error("Browser model missing from registry.");
    engine ??= await CreateMLCEngine(model,{initProgressCallback:p=>show(p.text)});
    const schema = {
      type: "object",
      properties: {id: {type: "integer", enum: Array.from({length: request.count + 1}, (_, i) => i)}},
      required: ["id"],
      additionalProperties: false
    };
    const reply = await engine.chat.completions.create({
      messages: request.messages,
      temperature: 0,
      max_tokens: 32,
      response_format: {type: "json_object", schema: JSON.stringify(schema)}
    });
    const choice = JSON.parse(reply.choices[0].message.content).id;
    Streamlit.setComponentValue({id: request.id, choice: String(choice)});
    show("Passage selection complete.");
  }catch(error){show(String(error));}finally{button.disabled=false;}
};
Streamlit.setComponentReady();
