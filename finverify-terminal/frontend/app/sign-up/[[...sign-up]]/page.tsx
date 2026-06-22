import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <SignUp
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "bg-[#0a0a0a] border border-t-border shadow-2xl",
          },
        }}
      />
    </div>
  );
}
