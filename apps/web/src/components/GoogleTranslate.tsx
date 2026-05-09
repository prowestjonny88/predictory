"use client";

import { useEffect, useState } from "react";
import Script from "next/script";

export default function GoogleTranslate() {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    // Define the initialization function on the window object
    // @ts-ignore
    window.googleTranslateElementInit = () => {
      // @ts-ignore
      new window.google.translate.TranslateElement(
        {
          pageLanguage: "en",
          autoDisplay: false,
          // ASEAN Languages: English, Malay, Tagalog, Indonesian, Thai, Vietnamese, Burmese, Khmer, Lao, Chinese (Simplified), Tamil
          includedLanguages: "en,ms,tl,id,th,vi,my,km,lo,zh-CN,ta",
        },
        "google_translate_element"
      );
    };
  }, []);

  // Prevent hydration mismatch by only rendering on the client
  if (!isClient) return null;

  return (
    <>
      <div id="google_translate_element" className="flex items-center"></div>
      <Script
        src="https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"
        strategy="afterInteractive"
      />
    </>
  );
}
