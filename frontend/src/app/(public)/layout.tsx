import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";

export default function PublicPagesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-[#050D12] text-[#E7EEF3]">
      <SiteHeader />
      <main className="flex-1 w-full">
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}
