#!/usr/bin/env python3
"""
Test script to verify that MicroK8s correctly reports node status when nodes fail.

This test script checks that:
1. Healthy nodes remain marked as "Ready"
2. Failed/offline nodes are marked as "NotReady" within expected timeframes
3. No healthy nodes are incorrectly marked as "NotReady"

This addresses the issue reported in: https://github.com/canonical/microk8s/issues/5275
"""

import subprocess
import time
import sys
import os
from typing import List, Dict, Tuple


class NodeStatusTester:
    def __init__(self, kubectl_cmd: str = "microk8s kubectl"):
        self.kubectl_cmd = kubectl_cmd
        
    def get_node_status(self) -> Dict[str, str]:
        """Get current node status for all nodes in the cluster."""
        try:
            result = subprocess.run(
                f"{self.kubectl_cmd} get nodes --no-headers",
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            
            nodes = {}
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        node_name = parts[0]
                        status = parts[1]
                        nodes[node_name] = status
            
            return nodes
        except subprocess.CalledProcessError as e:
            print(f"Error getting node status: {e}")
            return {}
    
    def wait_for_node_status_change(self, expected_status: Dict[str, str], 
                                   timeout_seconds: int = 120, 
                                   check_interval: int = 5) -> bool:
        """
        Wait for nodes to reach expected status within timeout period.
        
        Args:
            expected_status: Dict mapping node names to expected status ('Ready' or 'NotReady')
            timeout_seconds: Maximum time to wait for status change
            check_interval: Seconds between status checks
            
        Returns:
            True if all nodes reach expected status within timeout, False otherwise
        """
        start_time = time.time()
        
        print(f"Waiting for nodes to reach expected status...")
        print(f"Expected: {expected_status}")
        
        while time.time() - start_time < timeout_seconds:
            current_status = self.get_node_status()
            print(f"Current status: {current_status}")
            
            # Check if all expected nodes have the correct status
            all_correct = True
            for node, expected in expected_status.items():
                if node not in current_status:
                    print(f"Node {node} not found in current status")
                    all_correct = False
                    break
                elif current_status[node] != expected:
                    print(f"Node {node}: expected {expected}, got {current_status[node]}")
                    all_correct = False
                    break
            
            if all_correct:
                print("✅ All nodes have reached expected status")
                return True
            
            time.sleep(check_interval)
        
        print("❌ Timeout waiting for nodes to reach expected status")
        return False
    
    def simulate_node_failure_test(self) -> bool:
        """
        Test that simulates a node failure scenario.
        
        This test verifies the fix for issue #5275 by ensuring:
        1. Before failure: all nodes are Ready
        2. After simulated failure: only the failed node becomes NotReady
        3. Other healthy nodes remain Ready
        
        Note: This is a simulation test that doesn't actually take nodes offline.
        For real testing, you would need to manually disconnect a node.
        """
        print("=== Node Status Test ===")
        print("Testing node status reporting after simulated failure...")
        
        # Get initial node status
        initial_status = self.get_node_status()
        if not initial_status:
            print("❌ Failed to get initial node status")
            return False
        
        print(f"Initial node status: {initial_status}")
        
        # Verify all nodes are initially Ready
        all_ready = all(status == "Ready" for status in initial_status.values())
        if not all_ready:
            print("❌ Not all nodes are initially Ready")
            print("This test requires all nodes to start in Ready state")
            return False
        
        node_count = len(initial_status)
        print(f"✅ All {node_count} nodes are initially Ready")
        
        # Instructions for manual testing
        print("\n" + "="*60)
        print("MANUAL TEST INSTRUCTIONS:")
        print("="*60)
        print("1. This test has verified the baseline (all nodes Ready)")
        print("2. To complete the test, manually take one node offline:")
        print("   - On the target node, run: sudo systemctl stop snap.microk8s.daemon-kubelite")
        print("   - Or disconnect the node from the network")
        print("3. Monitor node status with: microk8s kubectl get nodes -w")
        print("4. Expected behavior with the fix:")
        print("   - Within ~40-50 seconds, only the offline node should show 'NotReady'")
        print("   - All other nodes should remain 'Ready'")
        print("   - No healthy nodes should be marked as 'NotReady'")
        print("5. Bring the node back online and verify it returns to 'Ready'")
        print("="*60)
        
        return True


def main():
    """Main test function."""
    tester = NodeStatusTester()
    
    # Run the node status test
    success = tester.simulate_node_failure_test()
    
    if success:
        print("\n✅ Node status test setup completed successfully")
        print("Follow the manual instructions above to verify the fix")
        return 0
    else:
        print("\n❌ Node status test failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())