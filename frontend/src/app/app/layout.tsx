import { ProductShell } from "@/components/ProductShell";
import "./product.css";

export default function AppLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <ProductShell>{children}</ProductShell>;
}
