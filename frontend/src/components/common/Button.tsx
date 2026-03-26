import type { ButtonHTMLAttributes, PropsWithChildren } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> { variant?: Variant; }

const styles: Record<Variant, string> = {
  primary: 'bg-[#0f3460] hover:bg-[#13457c] text-white border border-[#2a4d78]',
  secondary: 'bg-[#202a44] hover:bg-[#2b3654] text-slate-200 border border-[#2c3a61]',
  danger: 'bg-[#e94560] hover:bg-[#ff4f6b] text-white border border-[#f56d82]',
  ghost: 'bg-transparent hover:bg-[#1e2640] text-slate-200 border border-[#2b3554]',
};

export function Button({ children, className = '', variant = 'primary', ...props }: PropsWithChildren<Props>) {
  return <button className={`px-3 py-2 rounded-lg text-sm font-medium transition ${styles[variant]} ${className}`} {...props}>{children}</button>;
}
