/**
 * Renders an MCP elicitation request as a small modal form.
 *
 * `requestedSchema` is a flat JSON Schema (string / boolean / number properties
 * only, per the elicitation spec), so the form is built from whatever the server
 * asks for rather than from hardcoded fields.
 */
import type { ElicitProperty, ElicitRequest, ElicitResult } from "./mcpClient.ts";

const LONG_DESCRIPTION = 80;

export function renderElicitForm(request: ElicitRequest): Promise<ElicitResult> {
  return new Promise((resolve) => {
    const properties = request.requestedSchema?.properties ?? {};

    const overlay = document.createElement("div");
    overlay.className = "mcp-elicit-overlay";
    const modal = document.createElement("form");
    modal.className = "mcp-elicit-modal";

    const heading = document.createElement("p");
    heading.className = "mcp-elicit-message";
    heading.textContent = request.message ?? "Confirm this action";
    modal.appendChild(heading);

    const inputs = new Map<string, HTMLInputElement | HTMLTextAreaElement>();
    for (const [key, definition] of Object.entries(properties)) {
      const label = document.createElement("label");
      label.className = "mcp-elicit-field";
      const caption = document.createElement("span");
      caption.textContent = definition.title ?? key;
      label.appendChild(caption);

      const input = buildInput(key, definition);
      input.name = key;
      label.appendChild(input);

      if (definition.description) {
        const hint = document.createElement("small");
        hint.textContent = definition.description;
        label.appendChild(hint);
      }
      modal.appendChild(label);
      inputs.set(key, input);
    }

    const finish = (result: ElicitResult) => {
      overlay.remove();
      resolve(result);
    };

    const actions = document.createElement("div");
    actions.className = "mcp-elicit-actions";

    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "btn btn-ghost";
    cancel.textContent = "Cancel";
    cancel.addEventListener("click", () => finish({ action: "cancel" }));

    const accept = document.createElement("button");
    accept.type = "submit";
    accept.className = "btn btn-ok";
    accept.textContent = "Confirm";

    actions.append(cancel, accept);
    modal.appendChild(actions);

    modal.addEventListener("submit", (event) => {
      event.preventDefault();
      const content: Record<string, string | boolean> = {};
      for (const [key, input] of inputs) {
        content[key] = input instanceof HTMLInputElement && input.type === "checkbox" ? input.checked : input.value;
      }
      finish({ action: "accept", content });
    });

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    modal.querySelector<HTMLInputElement | HTMLTextAreaElement>("input, textarea")?.focus();
  });
}

function buildInput(key: string, definition: ElicitProperty): HTMLInputElement | HTMLTextAreaElement {
  if (definition.type === "boolean") {
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = definition.default !== undefined ? Boolean(definition.default) : false;
    return input;
  }
  if (
    key === "body" ||
    key === "message" ||
    key === "content" ||
    key === "prompt" ||
    (definition.description?.length ?? 0) > LONG_DESCRIPTION
  ) {
    const input = document.createElement("textarea");
    input.rows = key === "body" ? 8 : 3;
    input.value = definition.default != null ? String(definition.default) : "";
    return input;
  }
  const input = document.createElement("input");
  input.type = definition.format === "email" || key.includes("email") ? "email" : "text";
  input.value = definition.default != null ? String(definition.default) : "";
  return input;
}

export function injectElicitStyles(): void {
  const style = document.createElement("style");
  style.textContent = [
    ".mcp-elicit-overlay{position:fixed;inset:0;background:rgba(10,14,25,.55);display:flex;align-items:center;justify-content:center;z-index:300}",
    ".mcp-elicit-modal{background:#fff;border-radius:12px;padding:20px 22px;max-width:420px;width:90%;display:flex;flex-direction:column;gap:12px;font:14px/1.5 system-ui,sans-serif}",
    ".mcp-elicit-message{white-space:pre-wrap;margin:0 0 4px;color:#101827}",
    ".mcp-elicit-field{display:flex;flex-direction:column;gap:4px;font-size:13px;color:#374151}",
    ".mcp-elicit-field input[type=text],.mcp-elicit-field input[type=email],.mcp-elicit-field textarea{font:inherit;padding:7px 9px;border:1px solid #d0d5dd;border-radius:8px}",
    ".mcp-elicit-field small{color:#6b7280;font-size:11px}",
    ".mcp-elicit-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:4px}",
  ].join("");
  document.head.appendChild(style);
}
