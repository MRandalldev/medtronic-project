import {CreateMLCEngine} from "@mlc-ai/web-llm";

let enginePromise;
export function prepare() {
  if (!enginePromise) enginePromise = (async () => {
    const adapter = await navigator.gpu?.requestAdapter();
    if (!adapter) throw new Error("WebGPU unavailable");
    const precision = adapter.features.has("shader-f16") ? "f16" : "f32";
    return CreateMLCEngine(`Qwen2.5-0.5B-Instruct-q4${precision}_1-MLC`);
  })();
  return enginePromise;
}

export async function respond(messages, schema, dialogue) {
  const model = await prepare();
  if (dialogue) {
    const context = JSON.parse(messages.at(-1).content);
    const turns = context.recent_conversation.flatMap(turn => [
      {role:"user", content:turn.user}, {role:"assistant", content:turn.reco}
    ]);
    const completion = await model.chat.completions.create({
      messages:[{role:"system", content:"You are Reco, a recovery companion. Answer simple everyday questions briefly, warmly and honestly. Redirect explicit content or unrelated extensive tasks. Do not invent a human life, diagnoses, medical advice or patient information."},
        ...turns, {role:"user",content:context.latest_message}], temperature:0.3, max_tokens:100
    });
    return {kind:"social", reply:completion.choices[0].message.content, ids:[]};
  }
  const completion = await model.chat.completions.create({messages, temperature:0, max_tokens:180,
    response_format:{type:"json_object", schema:JSON.stringify(schema)}});
  return JSON.parse(completion.choices[0].message.content);
}
