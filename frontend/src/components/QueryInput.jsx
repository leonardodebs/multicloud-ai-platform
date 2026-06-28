// QueryInput: textarea + botão de envio + atalho de teclado Ctrl+Enter.
import { useState } from "react";

export default function QueryInput({ onSubmit, loading }) {
  const [text, setText] = useState("");

  const submit = () => {
    const trimmed = text.trim();
    if (trimmed && !loading) onSubmit(trimmed);
  };

  const handleKeyDown = (e) => {
    // Ctrl+Enter (ou Cmd+Enter no Mac) envia a pergunta.
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="query-input">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Digite sua pergunta...  (Ctrl+Enter para enviar)"
        rows={3}
        disabled={loading}
      />
      <button type="button" onClick={submit} disabled={loading || !text.trim()}>
        {loading ? "Consultando..." : "Consultar"}
      </button>
    </div>
  );
}
