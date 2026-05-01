import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "ComfyUI.iterationNode.lineNumbers",

    init() {
        const origSTRING = ComfyWidgets.STRING;

        ComfyWidgets.STRING = function (node, inputName, inputData) {
            const result = origSTRING.apply(this, arguments);

            if (!inputData[1]?.multiline || node.comfyClass !== "CombinerNode") {
                return result;
            }

            const widget = result.widget;
            const textarea = widget.inputEl;
            if (!textarea || textarea._hasLineNumbers) return result;
            textarea._hasLineNumbers = true;

            function addPrefixes(text) {
                const lines = text.split("\n");
                const updated = lines.map((line, i) => {
                    // Strip existing [N] prefix if present
                    const stripped = line.replace(/^\[\d+\]\s*/, "");
                    return `[${i}] ${stripped}`;
                });
                return updated.join("\n");
            }

            function stripPrefixes(text) {
                return text.replace(/^\[\d+\]\s*/gm, "");
            }

            // Add prefixes to initial value
            textarea.value = addPrefixes(textarea.value);

            // On input, re-number lines
            textarea.addEventListener("input", () => {
                const pos = textarea.selectionStart;
                const before = textarea.value.substring(0, pos);
                const lineIndex = before.split("\n").length - 1;

                const raw = stripPrefixes(textarea.value);
                const numbered = addPrefixes(raw);
                textarea.value = numbered;

                // Restore cursor position approximately
                const newLines = numbered.split("\n");
                let newPos = 0;
                for (let i = 0; i < lineIndex && i < newLines.length; i++) {
                    newPos += newLines[i].length + 1;
                }
                // Find where user was typing within the line
                const oldLineStart = before.lastIndexOf("\n") + 1;
                const oldPrefix = before.substring(oldLineStart).match(/^\[\d+\]\s*/);
                const prefixLen = oldPrefix ? oldPrefix[0].length : 0;
                const cursorInLine = pos - oldLineStart - prefixLen;

                const newPrefix = newLines[lineIndex]?.match(/^\[\d+\]\s*/);
                const newPrefixLen = newPrefix ? newPrefix[0].length : 0;
                newPos += newPrefixLen + Math.max(0, cursorInLine);

                textarea.selectionStart = textarea.selectionEnd = Math.min(newPos, numbered.length);
            });

            // Override widget value getter to strip prefixes for the backend
            const origSerialize = widget.serializeValue;
            widget.serializeValue = function (nodeId, widgetIndex) {
                const raw = stripPrefixes(textarea.value);
                // Restore prefixes in textarea after sending clean value
                requestAnimationFrame(() => {
                    textarea.value = addPrefixes(raw);
                });
                return raw;
            };

            return result;
        };
    }
});
