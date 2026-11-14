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
    const reply=await engine.chat.completions.create({messages:request.messages,temperature:0,max_tokens:8});
    Streamlit.setComponentValue({id:request.id,choice:reply.choices[0].message.content.trim()});
    show("Passage selection complete.");
  }catch(error){show(String(error));}finally{button.disabled=false;}
};
Streamlit.setComponentReady();
