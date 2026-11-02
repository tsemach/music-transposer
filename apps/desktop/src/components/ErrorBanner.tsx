interface Props {
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  onDismiss?: () => void;
}

export function ErrorBanner({ message, actionLabel, onAction, onDismiss }: Props) {
  return (
    <div role="alert" className="banner">
      <span>{message}</span>
      <span className="banner-actions">
        {actionLabel && onAction && (
          <button type="button" className="button button-small" onClick={onAction}>
            {actionLabel}
          </button>
        )}
        {onDismiss && (
          <button type="button" className="button button-small button-quiet" onClick={onDismiss}>
            Dismiss
          </button>
        )}
      </span>
    </div>
  );
}
