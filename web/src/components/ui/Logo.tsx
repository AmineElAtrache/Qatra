export default function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 2.5c-.3 0-.6.2-.8.4C9 6 5.5 10.4 5.5 14.2A6.5 6.5 0 0 0 12 20.7a6.5 6.5 0 0 0 6.5-6.5c0-3.8-3.5-8.2-5.7-11.3a1 1 0 0 0-.8-.4Z"
        fill="currentColor"
      />
      <path d="M9.2 14.4a2.9 2.9 0 0 0 2.8 2.9" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" fill="none" />
    </svg>
  );
}
