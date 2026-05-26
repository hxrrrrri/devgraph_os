import { useEffect, useMemo, useState } from "react";
import { Copy, ExternalLink, Maximize2, Minimize2, X } from "lucide-react";
import clsx from "clsx";
import { Highlight, themes } from "prism-react-renderer";
import ReactMarkdown from "react-markdown";
import { useDashboardStore } from "../store/dashboardStore";
import { client } from "../api/client";

interface FileContext {
  file_path: string;
  nodes: Array<{ id: string; qualified_name: string; line_start?: number | null; line_end?: number | null }>;
  chunks: Array<{ id: string; content: string; line_start?: number | null; line_end?: number | null; kind?: string }>;
}

const LANG_BY_EXT: Record<string, string> = {
  ts: "tsx", tsx: "tsx", js: "jsx", jsx: "jsx",
  py: "python", rb: "ruby", go: "go", rs: "rust",
  java: "java", kt: "kotlin", cs: "csharp",
  json: "json", yml: "yaml", yaml: "yaml", toml: "toml",
  sql: "sql", sh: "bash", bash: "bash",
  css: "css", scss: "scss", html: "markup",
  md: "markdown", mdx: "markdown", rst: "markdown",
};

function detectLanguage(path: string): string {
  const idx = path.lastIndexOf(".");
  if (idx < 0) return "plain";
  return LANG_BY_EXT[path.slice(idx + 1).toLowerCase()] ?? "plain";
}

function isMarkdown(language: string): boolean {
  return language === "markdown";
}

export function CodeViewer() {
  const open = useDashboardStore((s) => s.codeViewerOpen);
  const nodeId = useDashboardStore((s) => s.codeViewerNodeId);
  const expanded = useDashboardStore((s) => s.codeViewerExpanded);
  const closeCodeViewer = useDashboardStore((s) => s.closeCodeViewer);
  const toggleExpanded = useDashboardStore((s) => s.toggleCodeViewerExpanded);
  const nodesById = useDashboardStore((s) => s.nodesById);
  const [context, setContext] = useState<FileContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const changedLinesByFile = useDashboardStore((s) => s.changedLinesByFile);

  const node = nodeId ? nodesById.get(nodeId) : null;
  const filePath = node?.file_path ?? null;
  const language = useMemo(() => (filePath ? detectLanguage(filePath) : "plain"), [filePath]);
  const diffLines = useMemo(
    () => (filePath ? changedLinesByFile.get(filePath) ?? new Set<number>() : new Set<number>()),
    [filePath, changedLinesByFile],
  );

  useEffect(() => {
    if (!open || !filePath) {
      setContext(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    client
      .fileContext(filePath)
      .then((payload) => {
        if (!cancelled) setContext(payload as FileContext);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load file");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, filePath]);

  if (!open || !node || !filePath) return null;

  const chunks = context?.chunks ?? [];
  const stitched = chunks.map((c) => c.content).join("\n\n");

  function copyContent() {
    if (!stitched) return;
    void navigator.clipboard?.writeText(stitched);
  }

  const highlightRange: [number, number] | null =
    node.line_start && node.line_end ? [node.line_start, node.line_end] : null;

  return (
    <div className={clsx("dg-code-viewer", expanded && "is-expanded")} role="dialog" aria-modal={expanded}>
      <header className="dg-code-head">
        <div>
          <span className="eyebrow">file context</span>
          <h2>{filePath}</h2>
          <span className="dg-code-sub">{node.qualified_name} · {language}</span>
        </div>
        <div className="dg-code-actions">
          <button className="icon-button" onClick={copyContent} title="Copy file"><Copy size={14} /></button>
          <button
            className="icon-button"
            onClick={() => window.open(`/api/file-context?path=${encodeURIComponent(filePath)}`, "_blank")}
            title="Open raw JSON"
          >
            <ExternalLink size={14} />
          </button>
          <button className="icon-button" onClick={toggleExpanded} title={expanded ? "Collapse" : "Expand"}>
            {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
          <button className="icon-button" onClick={closeCodeViewer} aria-label="Close"><X size={14} /></button>
        </div>
      </header>

      {error ? <div className="alert">{error}</div> : null}
      {loading && chunks.length === 0 ? <div className="dg-code-loading">loading file context…</div> : null}

      {chunks.length === 0 && !loading ? (
        <div className="dg-code-empty">
          <p>No indexed chunks for this file.</p>
          <code>devgraph build</code>
        </div>
      ) : null}

      {chunks.length > 0 ? (
        isMarkdown(language) ? (
          <div className="dg-code-markdown">
            <ReactMarkdown>{stitched}</ReactMarkdown>
          </div>
        ) : (
          <div className="dg-code-stack">
            {chunks.map((chunk) => (
              <ChunkBlock
                key={chunk.id}
                chunk={chunk}
                language={language}
                highlightRange={highlightRange}
                diffLines={diffLines}
              />
            ))}
          </div>
        )
      ) : null}
    </div>
  );
}

function ChunkBlock({
  chunk,
  language,
  highlightRange,
  diffLines,
}: {
  chunk: FileContext["chunks"][number];
  language: string;
  highlightRange: [number, number] | null;
  diffLines: Set<number>;
}) {
  const startLine = chunk.line_start ?? 1;
  const inSelection = (line: number) => {
    if (!highlightRange) return false;
    return line >= highlightRange[0] && line <= highlightRange[1];
  };
  return (
    <section className="dg-code-chunk">
      <header className="dg-code-chunk-head">
        <span>L{chunk.line_start ?? "?"}{chunk.line_end ? `-${chunk.line_end}` : ""}</span>
        {chunk.kind ? <span className="dg-code-kind">{chunk.kind}</span> : null}
      </header>
      <Highlight code={chunk.content.replace(/\n$/, "")} language={language} theme={themes.nightOwl}>
        {({ className, style, tokens, getLineProps, getTokenProps }) => (
          <pre className={clsx("dg-code-pre", className)} style={style}>
            {tokens.map((line, idx) => {
              const actualLine = startLine + idx;
              const props = getLineProps({ line });
              const isChanged = diffLines.has(actualLine);
              return (
                <div
                  key={idx}
                  {...props}
                  className={clsx(
                    props.className,
                    inSelection(actualLine) && "is-highlight",
                    isChanged && "is-diff-line",
                  )}
                >
                  <span className="dg-code-lineno">{actualLine}</span>
                  {isChanged ? <span className="dg-code-diff-marker" aria-label="changed line">+</span> : null}
                  {line.map((token, ti) => {
                    const tProps = getTokenProps({ token });
                    return <span key={ti} {...tProps} />;
                  })}
                </div>
              );
            })}
          </pre>
        )}
      </Highlight>
    </section>
  );
}
