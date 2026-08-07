// Allow any authenticated caller to invoke read-only tools
permit(
  principal,
  action in [
    Action::"data-lookup___order_lookup",
    Action::"data-lookup___user_lookup",
    Action::"data-lookup___product_lookup",
    Action::"policy-retrieval___policy_retrieval"
  ],
  resource
);
