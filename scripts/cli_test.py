from __future__ import annotations

from core.analyzer import analyze


def main() -> None:
    print("أمانك: اكتب الرسالة اللي عندك، أو اكتب EXIT للخروج.")
    while True:
        text = input("رسالتك: ").strip()
        if not text:
            continue
        if text.lower() in {"exit", "خروج"}:
            print("شكراً لاستخدام أمانك.")
            break
        result = analyze(text, "cli")
        print(f"Verdict: {result.verdict} | score: {result.score}")
        print(f"Type: {result.scam_type}")
        print(result.reasons)
        print(f"Advice: {result.advice}")
        print("Links:", result.links_found)


if __name__ == "__main__":
    main()
