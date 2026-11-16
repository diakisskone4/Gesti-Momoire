/** Logo MemoAI (emblème « M » + tête IA). Source : public/brand/memoai-logo-full.png. */
export default function Logo({ size = 38, className = '' }: { size?: number; className?: string }) {
  return (
    <img className={`memoai-logo ${className}`} src="/brand/memoai-mark.png" width={size} height={size}
         alt="" aria-hidden="true" decoding="async" draggable={false} />
  );
}
