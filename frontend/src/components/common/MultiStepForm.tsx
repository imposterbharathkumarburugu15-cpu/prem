import React from 'react';
import { Check, ChevronRight, ChevronLeft, ArrowRight, Loader2 } from 'lucide-react';

export interface FormStep {
  id: string | number;
  label: string;
  description?: string;
  isValid?: boolean;
}

export interface MultiStepFormProps {
  steps: FormStep[];
  currentStep: number; // 0-based index
  onStepChange?: (step: number) => void;
  onPrev?: () => void;
  onNext?: () => void;
  onSubmit?: () => void;
  canProceed?: boolean;
  submitting?: boolean;
  submitLabel?: string;
  nextLabel?: string;
  prevLabel?: string;
  children: React.ReactNode;
  showFooter?: boolean;
  cancelButton?: React.ReactNode;
}

export const MultiStepForm: React.FC<MultiStepFormProps> = ({
  steps,
  currentStep,
  onStepChange,
  onPrev,
  onNext,
  onSubmit,
  canProceed = true,
  submitting = false,
  submitLabel = 'Confirm & Submit',
  nextLabel = 'Next Step',
  prevLabel = 'Back',
  children,
  showFooter = true,
  cancelButton,
}) => {
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%' }}>
      {/* STEPPERS HEADER */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #E5E7EB',
          paddingBottom: '16px',
          overflowX: 'auto',
          gap: '8px',
        }}
      >
        {steps.map((step, idx) => {
          const isCompleted = idx < currentStep;
          const isCurrent = idx === currentStep;

          return (
            <React.Fragment key={step.id}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  cursor: onStepChange && idx <= currentStep ? 'pointer' : 'default',
                  opacity: idx > currentStep ? 0.6 : 1,
                  flexShrink: 0,
                }}
                onClick={() => {
                  if (onStepChange && idx <= currentStep) {
                    onStepChange(idx);
                  }
                }}
              >
                {/* Step Circle */}
                <div
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '12px',
                    fontWeight: 700,
                    backgroundColor: isCompleted
                      ? '#1B4332'
                      : isCurrent
                      ? '#1B4332'
                      : '#F3F4F6',
                    color: isCompleted || isCurrent ? '#FFFFFF' : '#6B7280',
                    border: isCurrent ? '2px solid #40916C' : '1px solid transparent',
                    boxShadow: isCurrent ? '0 0 0 3px rgba(64, 145, 108, 0.2)' : 'none',
                    transition: 'all 0.2s ease',
                  }}
                >
                  {isCompleted ? <Check size={14} /> : idx + 1}
                </div>

                {/* Step Label */}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span
                    style={{
                      fontSize: '12px',
                      fontWeight: isCurrent ? 700 : 500,
                      color: isCurrent ? '#1B4332' : isCompleted ? '#111827' : '#6B7280',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {step.label}
                  </span>
                  {step.description && (
                    <span style={{ fontSize: '10px', color: '#9CA3AF' }}>
                      {step.description}
                    </span>
                  )}
                </div>
              </div>

              {idx < steps.length - 1 && (
                <div
                  style={{
                    flex: 1,
                    height: '2px',
                    backgroundColor: idx < currentStep ? '#1B4332' : '#E5E7EB',
                    minWidth: '16px',
                    margin: '0 4px',
                    transition: 'background-color 0.2s ease',
                  }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* STEP CONTENT BODY */}
      <div style={{ minHeight: '220px' }}>{children}</div>

      {/* FOOTER ACTIONS */}
      {showFooter && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderTop: '1px solid #E5E7EB',
            paddingTop: '16px',
            marginTop: '8px',
          }}
        >
          <div>
            {!isFirstStep ? (
              <button
                type="button"
                onClick={onPrev}
                disabled={submitting}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #D1D5DB',
                  color: '#374151',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: submitting ? 'not-allowed' : 'pointer',
                }}
              >
                <ChevronLeft size={16} />
                {prevLabel}
              </button>
            ) : (
              cancelButton || null
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {!isFirstStep && cancelButton}

            {!isLastStep ? (
              <button
                type="button"
                onClick={onNext}
                disabled={!canProceed || submitting}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 18px',
                  borderRadius: '6px',
                  backgroundColor: canProceed ? '#1B4332' : '#9CA3AF',
                  color: '#FFFFFF',
                  fontSize: '13px',
                  fontWeight: 600,
                  border: 'none',
                  cursor: canProceed && !submitting ? 'pointer' : 'not-allowed',
                  boxShadow: canProceed ? '0 1px 2px rgba(27, 67, 50, 0.2)' : 'none',
                }}
              >
                {nextLabel}
                <ChevronRight size={16} />
              </button>
            ) : (
              <button
                type="button"
                onClick={onSubmit}
                disabled={!canProceed || submitting}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 20px',
                  borderRadius: '6px',
                  backgroundColor: canProceed && !submitting ? '#1B4332' : '#9CA3AF',
                  color: '#FFFFFF',
                  fontSize: '13px',
                  fontWeight: 600,
                  border: 'none',
                  cursor: canProceed && !submitting ? 'pointer' : 'not-allowed',
                  boxShadow: canProceed ? '0 1px 3px rgba(27, 67, 50, 0.3)' : 'none',
                }}
              >
                {submitting && <Loader2 size={15} className="animate-spin" />}
                {submitting ? 'Committing...' : submitLabel}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
