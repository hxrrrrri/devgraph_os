import { type ButtonHTMLAttributes, type ReactNode } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: ReactNode;
};

export function Button({ icon, children, ...props }: ButtonProps) {
  return (
    <button className="dg-button" {...props}>
      {icon}
      {children ? <span>{children}</span> : null}
    </button>
  );
}

