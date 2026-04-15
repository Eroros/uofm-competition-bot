import rclpy
        self.task_pub = self.create_publisher(String, '/active_task', 10)
        self.status_sub = self.create_subscription(
            String,
            '/task_status',
            self.task_status_callback,
            10
        )

        self.nav_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')

        self.waypoints = {
            'antenna_4': [1.2, 0.8, 0.0],
            'antenna_2': [2.5, 1.5, 1.57],
            'crater_collection': [3.0, -1.2, 3.14],
            'return_home': [0.0, 0.0, 0.0]
        }

        self.start_next_task()

    def start_next_task(self):
        if self.current_index >= len(self.task_sequence):
            self.get_logger().info('Mission complete')
            return

        self.current_task = self.task_sequence[self.current_index]
        self.get_logger().info(f'Starting task: {self.current_task}')

        task_msg = String()
        task_msg.data = self.current_task
        self.task_pub.publish(task_msg)

        self.send_navigation_goal(self.current_task)

    def send_navigation_goal(self, task_name):
        if task_name not in self.waypoints:
            self.get_logger().error(f'No waypoint found for {task_name}')
            return

        x, y, yaw = self.waypoints[task_name]

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()

        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.orientation.z = yaw
        goal_msg.pose.pose.orientation.w = 1.0

        self.nav_client.wait_for_server()
        self.nav_client.send_goal_async(goal_msg)

    def task_status_callback(self, msg):
        if msg.data == 'complete':
            self.get_logger().info(f'Task complete: {self.current_task}')
            self.current_index += 1
            self.start_next_task()


def main(args=None):
    rclpy.init(args=args)
    node = MissionManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
