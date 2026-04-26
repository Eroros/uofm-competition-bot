<?xml version="1.0"?>
<!--
  secon26_bot URDF — 4-wheel skid-steer
  Hardware:
    - 4x DC motors, 2x TB6612FNG drivers
    - RPLidar C1 on laser_frame
    - MPU-9250 IMU on imu_link (I2C, address 0x68)
    - Front sonar for duck detection
    - IR link for Earth comms
  Dims in meters. Robot fits in 12"x12"x12" (0.3048m) start box.
-->
<robot name="secon26_bot">

  <link name="base_footprint"/>

  <joint name="base_footprint_joint" type="fixed">
    <parent link="base_footprint"/>
    <child link="base_link"/>
    <origin xyz="0 0 0.06" rpy="0 0 0"/>
  </joint>

  <link name="base_link">
    <visual>
      <geometry><box size="0.28 0.28 0.08"/></geometry>
      <material name="dark_gray"><color rgba="0.2 0.2 0.2 1"/></material>
    </visual>
    <collision>
      <geometry><box size="0.28 0.28 0.08"/></geometry>
    </collision>
    <inertial>
      <mass value="3.0"/>
      <inertia ixx="0.02" ixy="0" ixz="0" iyy="0.02" iyz="0" izz="0.04"/>
    </inertial>
  </link>

  <!-- Front Left wheel — Driver 1, Motor A -->
  <joint name="front_left_wheel_joint" type="continuous">
    <parent link="base_link"/>
    <child link="front_left_wheel"/>
    <origin xyz="0.10 0.15 -0.03" rpy="-1.5708 0 0"/>
    <axis xyz="0 0 1"/>
  </joint>
  <link name="front_left_wheel">
    <visual><geometry><cylinder radius="0.05" length="0.03"/></geometry>
      <material name="black"><color rgba="0.05 0.05 0.05 1"/></material></visual>
    <collision><geometry><cylinder radius="0.05" length="0.03"/></geometry></collision>
    <inertial><mass value="0.3"/>
      <inertia ixx="0.0003" ixy="0" ixz="0" iyy="0.0003" iyz="0" izz="0.0006"/></inertial>
  </link>

  <!-- Front Right wheel — Driver 1, Motor B -->
  <joint name="front_right_wheel_joint" type="continuous">
    <parent link="base_link"/>
    <child link="front_right_wheel"/>
    <origin xyz="0.10 -0.15 -0.03" rpy="1.5708 0 0"/>
    <axis xyz="0 0 1"/>
  </joint>
  <link name="front_right_wheel">
    <visual><geometry><cylinder radius="0.05" length="0.03"/></geometry>
      <material name="black"><color rgba="0.05 0.05 0.05 1"/></material></visual>
    <collision><geometry><cylinder radius="0.05" length="0.03"/></geometry></collision>
    <inertial><mass value="0.3"/>
      <inertia ixx="0.0003" ixy="0" ixz="0" iyy="0.0003" iyz="0" izz="0.0006"/></inertial>
  </link>

  <!-- Rear Left wheel — Driver 2, Motor A -->
  <joint name="rear_left_wheel_joint" type="continuous">
    <parent link="base_link"/>
    <child link="rear_left_wheel"/>
    <origin xyz="-0.10 0.15 -0.03" rpy="-1.5708 0 0"/>
    <axis xyz="0 0 1"/>
  </joint>
  <link name="rear_left_wheel">
    <visual><geometry><cylinder radius="0.05" length="0.03"/></geometry>
      <material name="black"><color rgba="0.05 0.05 0.05 1"/></material></visual>
    <collision><geometry><cylinder radius="0.05" length="0.03"/></geometry></collision>
    <inertial><mass value="0.3"/>
      <inertia ixx="0.0003" ixy="0" ixz="0" iyy="0.0003" iyz="0" izz="0.0006"/></inertial>
  </link>

  <!-- Rear Right wheel — Driver 2, Motor B -->
  <joint name="rear_right_wheel_joint" type="continuous">
    <parent link="base_link"/>
    <child link="rear_right_wheel"/>
    <origin xyz="-0.10 -0.15 -0.03" rpy="1.5708 0 0"/>
    <axis xyz="0 0 1"/>
  </joint>
  <link name="rear_right_wheel">
    <visual><geometry><cylinder radius="0.05" length="0.03"/></geometry>
      <material name="black"><color rgba="0.05 0.05 0.05 1"/></material></visual>
    <collision><geometry><cylinder radius="0.05" length="0.03"/></geometry></collision>
    <inertial><mass value="0.3"/>
      <inertia ixx="0.0003" ixy="0" ixz="0" iyy="0.0003" iyz="0" izz="0.0006"/></inertial>
  </link>

  <!-- IMU (MPU-9250) — I2C 0x68, SDA=GPIO2, SCL=GPIO3, INT=GPIO0 -->
  <joint name="imu_joint" type="fixed">
    <parent link="base_link"/>
    <child link="imu_link"/>
    <origin xyz="0 0 0.05" rpy="0 0 0"/>
  </joint>
  <link name="imu_link">
    <visual><geometry><box size="0.02 0.02 0.005"/></geometry>
      <material name="green"><color rgba="0.0 0.8 0.0 1"/></material></visual>
    <inertial><mass value="0.01"/>
      <inertia ixx="0.0000001" ixy="0" ixz="0" iyy="0.0000001" iyz="0" izz="0.0000001"/></inertial>
  </link>

  <!-- RPLidar C1 -->
  <joint name="lidar_joint" type="fixed">
    <parent link="base_link"/>
    <child link="laser_frame"/>
    <origin xyz="0 0 0.09" rpy="0 0 0"/>
  </joint>
  <link name="laser_frame">
    <visual><geometry><cylinder radius="0.04" length="0.04"/></geometry>
      <material name="red"><color rgba="0.8 0.1 0.1 1"/></material></visual>
    <collision><geometry><cylinder radius="0.04" length="0.04"/></geometry></collision>
    <inertial><mass value="0.17"/>
      <inertia ixx="0.00005" ixy="0" ixz="0" iyy="0.00005" iyz="0" izz="0.00005"/></inertial>
  </link>

  <!-- Front sonar (duck detection) -->
  <joint name="sonar_front_joint" type="fixed">
    <parent link="base_link"/>
    <child link="sonar_front_link"/>
    <origin xyz="0.145 0 0.01" rpy="0 0 0"/>
  </joint>
  <link name="sonar_front_link">
    <visual><geometry><box size="0.02 0.04 0.02"/></geometry>
      <material name="blue"><color rgba="0.1 0.1 0.8 1"/></material></visual>
    <inertial><mass value="0.02"/>
      <inertia ixx="0.000001" ixy="0" ixz="0" iyy="0.000001" iyz="0" izz="0.000001"/></inertial>
  </link>

  <!-- IR TX/RX (Earth comms) -->
  <joint name="ir_joint" type="fixed">
    <parent link="base_link"/>
    <child link="ir_link"/>
    <origin xyz="0 0 0.06" rpy="0 0 0"/>
  </joint>
  <link name="ir_link">
    <visual><geometry><box size="0.01 0.01 0.02"/></geometry>
      <material name="clear"><color rgba="0.9 0.9 0.9 1"/></material></visual>
    <inertial><mass value="0.01"/>
      <inertia ixx="0.0000001" ixy="0" ixz="0" iyy="0.0000001" iyz="0" izz="0.0000001"/></inertial>
  </link>

</robot>
