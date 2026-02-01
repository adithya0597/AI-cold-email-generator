import { SignUp as ClerkSignUp } from '@clerk/clerk-react';

export default function SignUp() {
  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <ClerkSignUp
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
        afterSignUpUrl="/onboarding"
      />
    </div>
  );
}
