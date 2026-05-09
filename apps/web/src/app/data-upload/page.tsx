"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, DatabaseZap, FileSpreadsheet, UploadCloud } from "lucide-react";

import { useCurrency } from "@/components/CurrencyProvider";
import Header from "@/components/Header";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { detectCurrencyFromCsvText, type CurrencyDetection } from "@/lib/currency";

export default function DataUploadPage() {
  const { t } = useLanguage();
  const { currency, setCurrencyCode } = useCurrency();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [redirecting, setRedirecting] = useState(false);
  const [result, setResult] = useState<{
    fileName: string;
    fileSizeMb: string;
    detectedCurrency: CurrencyDetection | null;
  } | null>(null);

  useEffect(() => {
    router.prefetch("/dashboard");
  }, [router]);

  const selectedFileLabel = useMemo(() => {
    if (!file) {
      return t("dataUpload.noFile", "No file selected");
    }
    return `${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`;
  }, [file, t]);

  async function handleDemoUpload() {
    if (!file || processing || redirecting) {
      return;
    }
    setProcessing(true);
    setResult(null);

    let detectedCurrency: CurrencyDetection | null = null;
    try {
      detectedCurrency = detectCurrencyFromCsvText(await file.text());
      if (detectedCurrency) {
        setCurrencyCode(detectedCurrency.currency.code);
      }
    } catch {
      detectedCurrency = null;
    }

    window.setTimeout(() => {
      setResult({
        fileName: file.name,
        fileSizeMb: (file.size / 1024 / 1024).toFixed(1),
        detectedCurrency,
      });
      setProcessing(false);
      setRedirecting(true);
      router.prefetch("/dashboard");

      window.setTimeout(() => {
        router.push("/dashboard");
      }, 1200);
    }, 900);
  }

  return (
    <div className="min-h-screen">
      <Header title={t("dataUpload.title", "POS / ERP Upload")} />

      <main className="mx-auto max-w-5xl space-y-6 p-6">
        <Card className="border-amber-200 bg-amber-50/40">
          <CardHeader>
            <div className="flex items-center gap-3">
              <DatabaseZap className="h-5 w-5 text-amber-600" />
              <CardTitle>{t("dataUpload.connectionTitle", "Connect bakery sales data")}</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-amber-900">
            <p>
              {t(
                "dataUpload.connectionCopy",
                "For the demo, this page mimics a POS/ERP connector by uploading a local CSV into the backend import pipeline."
              )}
            </p>
            <p>
              {t(
                "dataUpload.bakeryHint",
                "Upload Bakery sales.csv here. Predictory simulates connecting to the POS/ERP feed, then opens the Dashboard."
              )}
            </p>
          </CardContent>
        </Card>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <FileSpreadsheet className="h-5 w-5 text-neutral-500" />
                <CardTitle>{t("dataUpload.fileTitle", "Upload CSV")}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <label className="block rounded-xl border border-dashed border-neutral-300 bg-neutral-50 p-6 text-center transition hover:border-amber-300 hover:bg-amber-50/40">
                <UploadCloud className="mx-auto h-8 w-8 text-amber-500" />
                <span className="mt-3 block text-sm font-semibold text-neutral-900">
                  {t("dataUpload.chooseFile", "Choose a CSV file")}
                </span>
                <span className="mt-1 block text-xs text-neutral-500">{selectedFileLabel}</span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  className="sr-only"
                  onChange={(event) => {
                    setFile(event.target.files?.[0] ?? null);
                    setResult(null);
                    setRedirecting(false);
                  }}
                />
              </label>

              <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3 text-sm text-neutral-600">
                <p className="font-semibold text-neutral-900">
                  {t("dataUpload.demoDefaultsTitle", "Connector settings")}
                </p>
                <p className="mt-1">
                  {t(
                    "dataUpload.demoDefaultsCopy",
                    "Predictory reads the CSV for ASEAN country or currency markers and applies the matching symbol across the app."
                  )}
                </p>
                <p className="mt-2 text-xs font-medium text-neutral-500">
                  {t("dataUpload.activeCurrency", "Active currency")}: {currency.symbol} {currency.code}
                </p>
              </div>

              <Button
                type="button"
                onClick={handleDemoUpload}
                disabled={!file || processing || redirecting}
                className="w-full gap-2"
              >
                <UploadCloud className="h-4 w-4" />
                {redirecting
                  ? t("dataUpload.redirecting", "Preparing Dashboard...")
                  : processing
                    ? t("dataUpload.uploading", "Uploading...")
                  : t("dataUpload.upload", "Upload to POS / ERP connector")}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("dataUpload.resultTitle", "Import result")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!result && !processing && !redirecting && (
                <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-500">
                  {t("dataUpload.waiting", "Upload a CSV to simulate a POS/ERP handoff before opening the dashboard.")}
                </div>
              )}

              {(processing || result) && (
                <div className="space-y-4">
                  <div className="flex gap-3 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                    <div>
                      <p className="font-semibold">
                        {processing
                          ? t("dataUpload.connecting", "Connecting POS / ERP feed")
                          : t("dataUpload.complete", "CSV accepted")}
                      </p>
                      <p className="mt-1">
                        {processing
                          ? t("dataUpload.connectingCopy", "Checking the file and preparing the dashboard view.")
                          : t("dataUpload.completeCopy", "{{file}} is ready for the demo dashboard.", {
                              file: result?.fileName ?? "CSV",
                            })}
                      </p>
                    </div>
                  </div>

                  {(processing || redirecting) && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                      <div className="mb-2 flex items-center justify-between">
                        <span className="font-semibold">
                          {t("dataUpload.loadingDashboard", "Loading Dashboard")}
                        </span>
                        <span>{t("dataUpload.justMoment", "Just a moment")}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-amber-100">
                        <div className="h-full w-2/3 animate-pulse rounded-full bg-amber-500" />
                      </div>
                    </div>
                  )}

                  {result && (
                  <dl className="grid grid-cols-2 gap-3 text-sm">
                    <ResultMetric
                      label={t("dataUpload.file", "File")}
                      value={result.fileName}
                    />
                    <ResultMetric
                      label={t("dataUpload.size", "Size")}
                      value={`${result.fileSizeMb} MB`}
                    />
                    <ResultMetric
                      label={t("dataUpload.mode", "Mode")}
                      value={t("dataUpload.demoOnly", "CSV handoff")}
                    />
                    <ResultMetric
                      label={t("dataUpload.currency", "Currency")}
                      value={
                        result.detectedCurrency
                          ? `${result.detectedCurrency.currency.symbol} ${result.detectedCurrency.currency.code}`
                          : `${currency.symbol} ${currency.code}`
                      }
                    />
                  </dl>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}

function ResultMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
      <dt className="text-xs uppercase tracking-wide text-neutral-500">{label}</dt>
      <dd className="mt-1 text-lg font-semibold text-neutral-900">{value}</dd>
    </div>
  );
}
