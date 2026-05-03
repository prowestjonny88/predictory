"use client";

import { useLanguage } from "@/components/i18n/LanguageProvider";

export default function SkipLink() {
  const { t } = useLanguage();

  return (
    <a href="#main-content" className="skip-link">
      {t("common.skipToMain", "Skip to main content")}
    </a>
  );
}
