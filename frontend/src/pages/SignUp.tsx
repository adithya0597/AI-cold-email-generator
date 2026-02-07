import { SignUp as ClerkSignUp } from '@clerk/clerk-react';
import { Navigate } from 'react-router-dom';
import { isDevAuthMode } from '../providers/ClerkProvider';

export default function SignUp() {
  // Dev mode: already "signed in", redirect to dashboard
  if (isDevAuthMode) {
    return <Navigate to="/dashboard" replace />;
  }

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
