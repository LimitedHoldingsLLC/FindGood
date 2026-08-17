type Props = {
  className?: string;
  accentClassName?: string;
};

export function BrandMark({ className, accentClassName = "text-terracotta" }: Props) {
  return (
    <span className={className}>
      FindGood<span className={accentClassName}>.Food</span>
    </span>
  );
}
