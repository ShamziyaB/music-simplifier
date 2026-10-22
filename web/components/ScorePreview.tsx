"use client";

import { useEffect, useRef, useState } from "react";

type ScorePreviewProps = {
  musicxml: string;
};

export default function ScorePreview({ musicxml }: ScorePreviewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    let clear: (() => void) | undefined;

    setStatus("loading");
    setMessage("");

    const render = async () => {
      try {
        const { OpenSheetMusicDisplay } = await import("opensheetmusicdisplay");
        if (cancelled || !containerRef.current) return;

        containerRef.current.innerHTML = "";
        const osmd = new OpenSheetMusicDisplay(containerRef.current, {
          autoResize: true,
          drawTitle: false,
          drawComposer: false,
          drawCredits: false,
          drawPartNames: true,
          backend: "svg",
        });

        await osmd.load(musicxml);
        if (cancelled) return;

        osmd.zoom = 0.78;
        osmd.render();
        clear = () => osmd.clear();
        setStatus("ready");
      } catch (error) {
        console.error("OSMD render error", error);
        if (!cancelled) {
          setStatus("error");
          setMessage(
            error instanceof Error
              ? error.message
              : "Не удалось отрисовать ноты в браузере.",
          );
        }
      }
    };

    render();

    return () => {
      cancelled = true;
      try {
        clear?.();
      } catch {
        // ignore cleanup errors
      }
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [musicxml]);

  return (
    <div className="score-wrap">
      {status === "loading" && (
        <div className="score-status">Готовим предпросмотр нот…</div>
      )}
      {status === "error" && (
        <div className="score-status error">
          Не удалось показать ноты в браузере. Скачайте MusicXML и откройте его в
          MuseScore.
          {message ? ` (${message})` : ""}
        </div>
      )}
      <div
        ref={containerRef}
        className="score-canvas"
        style={{ display: status === "error" ? "none" : "block" }}
      />
    </div>
  );
}
