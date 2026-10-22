"use client";

import { useEffect, useRef, useState } from "react";
import ScorePreview from "@/components/ScorePreview";

type LevelKey = "easy" | "medium" | "medium_hard";

type LevelOption = {
  key: LevelKey;
  label: string;
  tagline: string;
  description: string;
  tag: string;
};

const LEVELS: LevelOption[] = [
  {
    key: "easy",
    label: "Легко",
    tagline: "Для самых первых шагов",
    description:
      "Трезвучия, без удвоений и лишних надстроек. Самый чистый вариант для начинающих.",
    tag: "Старт",
  },
  {
    key: "medium",
    label: "Средне",
    tagline: "Баланс простоты и звучания",
    description:
      "Убираются лишние звуки и удвоения, но аккорд может сохранить четвёртую ноту.",
    tag: "Баланс",
  },
  {
    key: "medium_hard",
    label: "Средне-сложно",
    tagline: "Ближе к оригиналу",
    description:
      "Минимальные вмешательства: только самые перегруженные аккорды и удобный диапазон.",
    tag: "Ближе",
  },
];

type PartInfo = {
  name: string;
  note_count: number;
  lowest: string | null;
  highest: string | null;
  mean_ps: number | null;
};

type SimplifyResult = {
  filename: string;
  level: LevelKey;
  level_label: string;
  musicxml: string;
  midi_base64: string | null;
  report: string;
  info: {
    key: string;
    time_signature: string | null;
    tempo_bpm: number | null;
    parts: PartInfo[];
  };
  validation: {
    ok: boolean;
    errors: string[];
    warnings: string[];
  };
  stats: {
    changes: number;
    chord_reductions: number;
    range_shifts: number;
    parts: number;
    note_events_before: number;
    note_events_after: number;
  };
};

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

const apiUrl = (path: string) => `${API_BASE}${path}`;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

function baseName(filename: string): string {
  return filename.replace(/\.[^.]+$/, "");
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result ?? "");
      resolve(result.includes(",") ? result.split(",")[1] : result);
    };
    reader.onerror = () => reject(new Error("Не удалось прочитать файл."));
    reader.readAsDataURL(file);
  });
}

function downloadBlob(data: BlobPart | Blob, filename: string, type: string) {
  const blob = data instanceof Blob ? data : new Blob([data], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [fileBase64, setFileBase64] = useState("");
  const [level, setLevel] = useState<LevelKey>("medium");
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SimplifyResult | null>(null);
  const [tab, setTab] = useState<"score" | "report">("score");

  const inputRef = useRef<HTMLInputElement | null>(null);
  const resultRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(apiUrl("/api/health"), {
      cache: "no-store",
      signal: controller.signal,
    }).catch(() => {
      // Бэкенд может быть ещё не запущен — ошибку покажем при обработке.
    });
    return () => controller.abort();
  }, []);

  async function acceptFile(candidate: File) {
    setError(null);
    const extension = candidate.name.split(".").pop()?.toLowerCase() ?? "";
    if (!["musicxml", "xml", "mxl"].includes(extension)) {
      setError("Поддерживаются файлы MusicXML, XML и MXL. PDF и фото пока нельзя.");
      return;
    }
    if (candidate.size > 3 * 1024 * 1024) {
      setError("Файл слишком большой. Максимальный размер — 3 МБ.");
      return;
    }

    try {
      const encoded = await fileToBase64(candidate);
      setFile(candidate);
      setFileBase64(encoded);
      setResult(null);
    } catch {
      setError("Не удалось прочитать файл. Попробуйте другой.");
    }
  }

  async function loadSample() {
    setError(null);
    try {
      const response = await fetch("/piano_sample.musicxml");
      if (!response.ok) throw new Error("sample");
      const text = await response.text();
      const sample = new File([text], "piano_sample.musicxml", {
        type: "application/vnd.recordare.musicxml+xml",
      });
      await acceptFile(sample);
    } catch {
      setError("Не удалось загрузить пример. Попробуйте выбрать свой файл.");
    }
  }

  async function processScore() {
    if (!file || !fileBase64) {
      setError("Сначала загрузите MusicXML.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(apiUrl("/api/simplify"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          level,
          content_base64: fileBase64,
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Сервис не смог обработать файл. Попробуйте ещё раз.",
        );
      }

      setResult(data as SimplifyResult);
      setTab("score");
      window.setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    } catch (caught) {
      if (caught instanceof TypeError) {
        setError(
          "Не удалось связаться с сервером обработки. Проверьте, что API запущен и доступен.",
        );
      } else {
        setError(
          caught instanceof Error ? caught.message : "Не удалось обработать файл.",
        );
      }
    } finally {
      setIsLoading(false);
    }
  }

  function reset() {
    setFile(null);
    setFileBase64("");
    setResult(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function downloadMusicXml() {
    if (!result) return;
    downloadBlob(
      result.musicxml,
      `${baseName(result.filename)}_${result.level}.musicxml`,
      "application/vnd.recordare.musicxml+xml",
    );
  }

  function downloadMidi() {
    if (!result?.midi_base64) return;
    const bytes = Uint8Array.from(atob(result.midi_base64), (char) =>
      char.charCodeAt(0),
    );
    downloadBlob(
      new Blob([bytes], { type: "audio/midi" }),
      `${baseName(result.filename)}_${result.level}.mid`,
      "audio/midi",
    );
  }

  function downloadReport() {
    if (!result) return;
    downloadBlob(
      result.report,
      `${baseName(result.filename)}_${result.level}.report.txt`,
      "text/plain;charset=utf-8",
    );
  }

  return (
    <main className="page">
      <header className="hero">
        <div className="brand">
          <span className="brand-mark">♪</span>
          Music Simplifier
        </div>
        <div className="eyebrow">MusicXML → проще</div>
        <h1>
          Ноты, которые <em>звучат</em>,
          <br />
          но играть проще.
        </h1>
        <p>
          Загрузите ноты в MusicXML — программа уберёт лишние ноты и неудобные
          аккорды. Выберите уровень, посмотрите результат и скачайте файл для
          MuseScore.
        </p>
      </header>

      <section className="workspace" aria-label="Загрузка и упрощение нот">
        <div className="panel">
          <div className="panel-head">
            <span className="step">01</span>
            <h2>Загрузите ноты</h2>
          </div>

          <div
            className={`dropzone${isDragging ? " dragging" : ""}${
              file ? " has-file" : ""
            }`}
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                inputRef.current?.click();
              }
            }}
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setIsDragging(false);
              const dropped = event.dataTransfer.files?.[0];
              if (dropped) void acceptFile(dropped);
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".musicxml,.xml,.mxl,application/vnd.recordare.musicxml+xml"
              hidden
              onChange={(event) => {
                const selected = event.target.files?.[0];
                if (selected) void acceptFile(selected);
                event.target.value = "";
              }}
            />
            {file ? (
              <>
                <div className="upload-icon">♪</div>
                <h3>{file.name}</h3>
                <p>{formatBytes(file.size)} · нажмите, чтобы заменить файл</p>
                <span className="file-pill">
                  <span>MusicXML готов к обработке</span>
                </span>
              </>
            ) : (
              <>
                <div className="upload-icon">↑</div>
                <h3>Перетащите файл сюда</h3>
                <p>
                  или нажмите, чтобы выбрать
                  <br />
                  MusicXML, XML или MXL
                </p>
              </>
            )}
          </div>

          <button className="sample-button" type="button" onClick={loadSample}>
            Нет файла? Попробовать пример →
          </button>
          <p className="hint">До 3 МБ · файл не сохраняется на сервере</p>
        </div>

        <div className="panel">
          <div className="panel-head">
            <span className="step">02</span>
            <h2>Выберите уровень</h2>
          </div>

          <div className="level-list" role="group" aria-label="Уровень сложности">
            {LEVELS.map((option) => (
              <button
                key={option.key}
                type="button"
                className={`level-card${level === option.key ? " active" : ""}`}
                aria-pressed={level === option.key}
                onClick={() => setLevel(option.key)}
              >
                <span className="level-radio" aria-hidden="true" />
                <span className="level-copy">
                  <strong>{option.label}</strong>
                  <span>{option.tagline}</span>
                  <span>{option.description}</span>
                </span>
                <span className="level-tag">{option.tag}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="action-panel">
          <div className="action-copy">
            <strong>Готовы упростить?</strong>
            <span>
              {file
                ? `Файл: ${file.name} · уровень «${
                    LEVELS.find((item) => item.key === level)?.label
                  }»`
                : "Сначала выберите файл с нотами"}
            </span>
          </div>
          <button
            className="submit"
            type="button"
            disabled={!file || isLoading}
            onClick={() => void processScore()}
          >
            {isLoading ? (
              <>
                <span className="spinner" aria-hidden="true" />
                Упрощаем ноты…
              </>
            ) : (
              "Упростить ноты"
            )}
          </button>
        </div>
      </section>

      {error && <div className="error-box">{error}</div>}

      {result && (
        <section className="result" ref={resultRef} aria-live="polite">
          <div className="result-head">
            <div>
              <div className="eyebrow">Готово</div>
              <h2>{result.filename}</h2>
              <p className="result-sub">
                Уровень «{result.level_label}» · {result.stats.parts}{" "}
                {result.stats.parts === 1 ? "партия" : "партии"}
              </p>
            </div>
            <div className="downloads">
              <button
                className="download primary"
                type="button"
                onClick={downloadMusicXml}
              >
                Скачать MusicXML
              </button>
              {result.midi_base64 && (
                <button className="download" type="button" onClick={downloadMidi}>
                  MIDI
                </button>
              )}
              <button className="download" type="button" onClick={downloadReport}>
                Отчёт
              </button>
            </div>
          </div>

          <div className="result-meta">
            <span className="meta-chip">
              Тональность: <b>{result.info.key}</b>
            </span>
            <span className="meta-chip">
              Размер: <b>{result.info.time_signature ?? "не указан"}</b>
            </span>
            {result.info.tempo_bpm && (
              <span className="meta-chip">
                Темп: <b>{Math.round(result.info.tempo_bpm)} BPM</b>
              </span>
            )}
            <span className="meta-chip">
              Нот до / после:{" "}
              <b>
                {result.stats.note_events_before} / {result.stats.note_events_after}
              </b>
            </span>
          </div>

          <div className="stats">
            <div className="stat">
              <strong>{result.stats.changes}</strong>
              <span>всего изменений</span>
            </div>
            <div className="stat">
              <strong>{result.stats.chord_reductions}</strong>
              <span>аккордов упрощено</span>
            </div>
            <div className="stat">
              <strong>{result.stats.range_shifts}</strong>
              <span>нот перенесено в диапазон</span>
            </div>
          </div>

          {!result.validation.ok && (
            <div className="notice error">
              Проверка нашла ошибки: {result.validation.errors.join(" ")}
            </div>
          )}

          {result.validation.warnings.length > 0 && (
            <div className="notice warn">
              <b>Проверьте на слух:</b>{" "}
              {result.validation.warnings.slice(0, 3).join(" ")}
              {result.validation.warnings.length > 3
                ? ` Ещё ${result.validation.warnings.length - 3} — в отчёте.`
                : ""}
            </div>
          )}

          <div className="tabs">
            <button
              className={`tab${tab === "score" ? " active" : ""}`}
              type="button"
              onClick={() => setTab("score")}
            >
              Ноты
            </button>
            <button
              className={`tab${tab === "report" ? " active" : ""}`}
              type="button"
              onClick={() => setTab("report")}
            >
              Отчёт
            </button>
          </div>

          {tab === "score" ? (
            <ScorePreview musicxml={result.musicxml} />
          ) : (
            <pre className="report">{result.report}</pre>
          )}

          <div className="result-actions">
            <span className="result-sub">
              Проверьте результат глазами и на слух перед разучиванием.
            </span>
            <button className="reset" type="button" onClick={reset}>
              Обработать другой файл
            </button>
          </div>
        </section>
      )}

      <section className="how" aria-label="Как это работает">
        <div className="how-item">
          <span>01</span>
          <h3>MusicXML — это удобно</h3>
          <p>
            Экспортируйте ноты из MuseScore, Finale или другого редактора в
            MusicXML. PDF и фото пока не поддерживаются.
          </p>
        </div>
        <div className="how-item">
          <span>02</span>
          <h3>Три уровня сложности</h3>
          <p>
            От простых трезвучий до бережного упрощения. Можно сравнить уровни и
            выбрать тот, который удобно играть.
          </p>
        </div>
        <div className="how-item">
          <span>03</span>
          <h3>Всё под контролем</h3>
          <p>
            Рядом с нотами появляется отчёт: что изменилось и что стоит проверить
            вручную. Файлы не хранятся на сервере.
          </p>
        </div>
      </section>

      <footer className="footer">
        <span>
          Только для личного учебного использования. Не распространяйте ноты,
          защищённые авторским правом.
        </span>
        <span>
          <a
            href="https://github.com/ShamziyaB/music-simplifier"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>{" "}
          · Music Simplifier
        </span>
      </footer>
    </main>
  );
}
