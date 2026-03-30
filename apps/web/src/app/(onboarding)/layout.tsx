export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background font-sans antialiased">
      <div className="mx-auto flex min-h-screen max-w-4xl flex-col items-center justify-center">
        {children}
      </div>
    </div>
  );
}
