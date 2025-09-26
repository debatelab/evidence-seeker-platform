# Email Verification Implementation Plan

## Overview
Implement email verification for user accounts to enhance security and user trust. This feature will require users to verify their email addresses before gaining full access to the platform, preventing spam accounts and ensuring valid contact information.

## Current State Analysis

### Existing Infrastructure
- **fastapi-users Library**: Already integrated with verification support
- **User Model**: `is_verified` boolean field exists
- **Verification Router**: Already included in auth endpoints (`/auth/verify`)
- **UserManager**: Has verification hooks (`on_after_request_verify`)
- **JWT Authentication**: Bearer token system in place

### What's Missing
- Email service for sending verification emails
- Email templates and content
- SMTP configuration
- Frontend verification flow
- Resend verification functionality
- User verification status display
- Email verification enforcement

## Implementation Strategy

### Phase 1: Email Service Infrastructure

#### 1.1 Add Email Dependencies
```bash
# Add to backend/requirements.txt
fastapi-mail==1.4.1
jinja2==3.1.2  # For email templates
```

#### 1.2 Email Configuration
Add email settings to `backend/app/core/config.py`:

```python
# Email settings
smtp_server: str = "smtp.gmail.com"
smtp_port: int = 587
smtp_username: str = ""
smtp_password: str = ""
email_from: str = "noreply@evidence-seeker.com"
email_from_name: str = "Evidence Seeker Platform"

# Email templates
email_templates_dir: str = "backend/app/templates/email"
```

#### 1.3 Email Service Module
Create `backend/app/core/email_service.py`:

```python
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from typing import List
from app.core.config import settings

class EmailService:
    def __init__(self):
        self.config = ConnectionConfig(
            MAIL_USERNAME=settings.smtp_username,
            MAIL_PASSWORD=settings.smtp_password,
            MAIL_FROM=settings.email_from,
            MAIL_PORT=settings.smtp_port,
            MAIL_SERVER=settings.smtp_server,
            MAIL_FROM_NAME=settings.email_from_name,
            MAIL_TLS=True,
            MAIL_SSL=False,
            USE_CREDENTIALS=True,
            TEMPLATE_FOLDER=settings.email_templates_dir,
        )
        self.fast_mail = FastMail(self.config)

    async def send_verification_email(self, email: EmailStr, token: str):
        """Send email verification link"""
        # Implementation with template rendering

    async def send_password_reset_email(self, email: EmailStr, token: str):
        """Send password reset email"""
        # Implementation
```

#### 1.4 Email Templates
Create email template directory structure:
```
backend/app/templates/email/
├── verify_email.html
├── verify_email.txt
├── reset_password.html
└── reset_password.txt
```

### Phase 2: Backend Email Integration

#### 2.1 Update UserManager
Modify `backend/app/core/auth.py` to integrate email sending:

```python
from app.core.email_service import EmailService

class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    def __init__(self, user_db, email_service: EmailService):
        super().__init__(user_db)
        self.email_service = email_service

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Send verification email after verification request"""
        await self.email_service.send_verification_email(user.email, token)
        print(f"Verification email sent to {user.email}")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Send password reset email"""
        await self.email_service.send_password_reset_email(user.email, token)
        print(f"Password reset email sent to {user.email}")
```

#### 2.2 Email Verification Enforcement
Add middleware or dependency to enforce email verification:

```python
# In backend/app/core/auth.py
async def get_current_verified_user(user: User = Depends(get_current_user)) -> User:
    """Get current user and ensure they are verified"""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first."
        )
    return user
```

#### 2.3 Additional API Endpoints
Add resend verification endpoint in `backend/app/api/auth.py`:

```python
@router.post("/auth/resend-verification")
async def resend_verification(
    request: Request,
    user_manager: UserManager = Depends(get_user_manager)
):
    """Resend verification email to current user"""
    # Implementation
```

### Phase 3: Database Updates

#### 3.1 Migration for Email Verification Fields
Create Alembic migration to add email verification tracking:

```python
# Add to migration file
op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
op.add_column('users', sa.Column('verification_token_expires', sa.DateTime(), nullable=True))
op.add_column('users', sa.Column('email_verified_at', sa.DateTime(), nullable=True))
```

#### 3.2 Update User Model
Add new fields to `backend/app/models/user.py`:

```python
verification_token = Column(String, nullable=True)
verification_token_expires = Column(DateTime, nullable=True)
email_verified_at = Column(DateTime, nullable=True)
```

### Phase 4: Frontend Email Verification Flow

#### 4.1 Email Verification Component
Create `frontend/src/components/Auth/EmailVerification.tsx`:

```typescript
interface EmailVerificationProps {
  email: string;
  onVerificationComplete: () => void;
  onResendEmail: () => void;
}

const EmailVerification: React.FC<EmailVerificationProps> = ({
  email,
  onVerificationComplete,
  onResendEmail
}) => {
  // Implementation with verification form and resend functionality
};
```

#### 4.2 Update Auth Context
Modify `frontend/src/context/AuthContext.tsx` to handle verification state:

```typescript
interface AuthContextType {
  user: User | null;
  isVerified: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: RegisterData) => Promise<void>;
  verifyEmail: (token: string) => Promise<void>;
  resendVerification: () => Promise<void>;
  logout: () => void;
}
```

#### 4.3 Update Registration Flow
Modify `frontend/src/components/Auth/RegisterForm.tsx` to redirect to verification page:

```typescript
const handleRegister = async (formData: RegisterFormData) => {
  try {
    await register(formData);
    navigate('/verify-email', {
      state: { email: formData.email }
    });
  } catch (error) {
    // Handle error
  }
};
```

#### 4.4 Verification Page
Create `frontend/src/pages/VerifyEmail.tsx`:

```typescript
const VerifyEmail: React.FC = () => {
  const location = useLocation();
  const email = location.state?.email;

  // Implementation with token handling from URL params
};
```

#### 4.5 Update Login Flow
Modify `frontend/src/components/Auth/LoginForm.tsx` to check verification status:

```typescript
const handleLogin = async (formData: LoginFormData) => {
  try {
    const user = await login(formData);
    if (!user.is_verified) {
      navigate('/verify-email', {
        state: { email: user.email, showResend: true }
      });
      return;
    }
    navigate('/dashboard');
  } catch (error) {
    // Handle error
  }
};
```

### Phase 5: User Experience Enhancements

#### 5.1 Verification Status Display
Add verification status to user profile components:

```typescript
// In user profile components
{!user.is_verified && (
  <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
    <div className="flex">
      <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
      <div className="ml-3">
        <h3 className="text-sm font-medium text-yellow-800">
          Email not verified
        </h3>
        <div className="mt-2 text-sm text-yellow-700">
          <p>Please verify your email to access all features.</p>
        </div>
        <div className="mt-4">
          <button
            onClick={handleResendVerification}
            className="bg-yellow-100 hover:bg-yellow-200 text-yellow-800 px-3 py-2 rounded-md text-sm font-medium"
          >
            Resend verification email
          </button>
        </div>
      </div>
    </div>
  </div>
)}
```

#### 5.2 Email Verification Banner
Add persistent banner for unverified users across the app.

#### 5.3 Success Feedback
Show success messages after email verification and resend actions.

### Phase 6: Testing & Validation

#### 6.1 Backend Tests
Add tests in `backend/tests/test_email_verification.py`:

```python
def test_send_verification_email():
    # Test email sending functionality

def test_verification_token_validation():
    # Test token validation

def test_verified_user_access():
    # Test that verified users can access protected endpoints

def test_unverified_user_restriction():
    # Test that unverified users are restricted
```

#### 6.2 Frontend Tests
Add tests for verification components and flows.

#### 6.3 Integration Tests
Test complete email verification flow from registration to verification.

### Phase 7: Configuration & Deployment

#### 7.1 Environment Variables
Update `.env` files with email configuration:

```env
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@evidence-seeker.com
EMAIL_FROM_NAME=Evidence Seeker Platform
```

#### 7.2 Docker Configuration
Update `docker-compose.yml` to include email service if needed.

#### 7.3 Documentation
Update README.md with email verification setup instructions.

## Implementation Checklist

### Phase 1: Email Infrastructure
- [ ] Add email dependencies to requirements.txt
- [ ] Add email settings to config.py
- [ ] Create EmailService class
- [ ] Create email templates
- [ ] Test email sending functionality

### Phase 2: Backend Integration
- [ ] Update UserManager with email service
- [ ] Implement verification enforcement middleware
- [ ] Add resend verification endpoint
- [ ] Update verification hooks

### Phase 3: Database Changes
- [ ] Create migration for verification fields
- [ ] Update User model with new fields
- [ ] Run migration on all environments

### Phase 4: Frontend Implementation
- [ ] Create EmailVerification component
- [ ] Update AuthContext for verification state
- [ ] Modify registration flow
- [ ] Create verification page
- [ ] Update login flow for verification checks

### Phase 5: UX Enhancements
- [ ] Add verification status display
- [ ] Implement verification banner
- [ ] Add success feedback messages
- [ ] Style verification components

### Phase 6: Testing
- [ ] Write backend unit tests
- [ ] Write frontend component tests
- [ ] Create integration tests
- [ ] Test email delivery

### Phase 7: Deployment
- [ ] Update environment configurations
- [ ] Update Docker setup if needed
- [ ] Update documentation
- [ ] Deploy and test in staging

## Success Criteria

1. **Email Delivery**: Verification emails are sent successfully
2. **Token Validation**: Verification tokens work correctly
3. **User Experience**: Clear flow from registration to verification
4. **Security**: Unverified users cannot access protected features
5. **Resend Functionality**: Users can request new verification emails
6. **Status Display**: Users can see their verification status
7. **Error Handling**: Proper error messages for failed verifications

## Risk Assessment

- **Medium Risk**: Email deliverability issues with SMTP providers
- **Low Risk**: Frontend changes are additive
- **Low Risk**: Database changes are backward compatible
- **Medium Risk**: SMTP configuration complexity

## Rollback Plan

If issues arise:
1. Remove email verification enforcement (allow unverified access)
2. Revert UserManager changes to disable email sending
3. Keep database fields for future re-enablement
4. Remove frontend verification components

## Dependencies

- SMTP email service (Gmail, SendGrid, etc.)
- Email templates (HTML + text versions)
- Frontend routing updates
- Database migration

## Timeline Estimate

- Phase 1 (Infrastructure): 4-6 hours
- Phase 2 (Backend): 6-8 hours
- Phase 3 (Database): 2-3 hours
- Phase 4 (Frontend): 8-10 hours
- Phase 5 (UX): 4-6 hours
- Phase 6 (Testing): 6-8 hours
- Phase 7 (Deployment): 2-4 hours

**Total Estimate**: 32-45 hours

## Post-MVP Enhancements

- Email verification analytics
- Bulk verification management for admins
- Custom email templates per organization
- SMS verification fallback
- Email verification expiration and cleanup
