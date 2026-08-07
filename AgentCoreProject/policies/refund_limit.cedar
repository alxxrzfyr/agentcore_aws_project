// Allow refunds under $500 for any authenticated caller
permit(
  principal,
  action == Action::"refund-target___process_refund",
  resource
) when {
  context.input.amount < 500
};
