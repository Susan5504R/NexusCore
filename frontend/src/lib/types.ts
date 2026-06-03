export interface GraphStreamStateDelta {
  active_node?: string;
  retry_count?: number;
  execution_exit_code?: number;
  security_clearance?: boolean;
  proposed_patch?: string;
  latest_message?: string;
  token_consumption?: number;
}

export interface GraphStreamEvent {
  event: "node_update" | "complete" | "error";
  run_id: string;
  node?: string;
  state?: GraphStreamStateDelta;
  error?: string;
}
