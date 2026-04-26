<?xml version="1.0" ?>
<!--
  IEEE SoutheastCon 2026 Arena — Gazebo Harmonic World
  Arena base: 4ft x 8ft = 1.2192m x 2.4384m
  Origin (0,0) = center of arena floor
  North wall = +Y, South wall = -Y, East = +X, West = -X

  Areas (from rulebook):
    Area 1 (blue)   = lower-left  quadrant — Starting area + Antenna #4
    Area 2 (green)  = upper-left  quadrant — Antenna #1 + Lunar Landing area
    Area 3 (purple) = right half             — Antenna #2
    Area 4 (red)    = crater, right-center  — Antenna #3 (inside crater)

  Antenna orientations (rulebook):
    #1 faces south  (button task)
    #2 faces south  (crank task)
    #3 faces west   (pressure plate / duck on top)
    #4 faces north  (keypad task)
-->
<sdf version="1.9">
  <world name="secon26_arena">

    <!-- Physics -->
    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

    <!-- Plugins (Gazebo Harmonic) -->
    <plugin filename="gz-sim-physics-system"            name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-sensors-system"            name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="gz-sim-user-commands-system"      name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system"  name="gz::sim::systems::SceneBroadcaster"/>

    <!-- Light -->
    <light name="sun" type="directional">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <specular>0.3 0.3 0.3 1</specular>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <!-- ===== ARENA FLOOR ===== -->
    <model name="arena_floor">
      <static>true</static>
      <pose>0 0 0 0 0 0</pose>
      <link name="link">
        <collision name="col">
          <geometry><box><size>2.4384 1.2192 0.01</size></box></geometry>
        </collision>
        <visual name="vis">
          <geometry><box><size>2.4384 1.2192 0.01</size></box></geometry>
          <material>
            <ambient>0.08 0.08 0.08 1</ambient>
            <diffuse>0.08 0.08 0.08 1</diffuse>
          </material>
        </visual>
      </link>
    </model>

    <!-- ===== BORDER WALLS (1x8 boards ~18cm tall) ===== -->
    <!-- North wall -->
    <model name="wall_north">
      <static>true</static>
      <pose>0 0.6096 0.1 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>2.4384 0.025 0.2</size></box></geometry></collision>
        <visual name="vis">
          <geometry><box><size>2.4384 0.025 0.2</size></box></geometry>
          <material><ambient>0.08 0.08 0.08 1</ambient><diffuse>0.08 0.08 0.08 1</diffuse></material>
        </visual>
      </link>
    </model>
    <!-- South wall -->
    <model name="wall_south">
      <static>true</static>
      <pose>0 -0.6096 0.1 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>2.4384 0.025 0.2</size></box></geometry></collision>
        <visual name="vis">
          <geometry><box><size>2.4384 0.025 0.2</size></box></geometry>
          <material><ambient>0.08 0.08 0.08 1</ambient><diffuse>0.08 0.08 0.08 1</diffuse></material>
        </visual>
      </link>
    </model>
    <!-- West wall -->
    <model name="wall_west">
      <static>true</static>
      <pose>-1.2192 0 0.1 0 0 1.5708</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>1.2192 0.025 0.2</size></box></geometry></collision>
        <visual name="vis">
          <geometry><box><size>1.2192 0.025 0.2</size></box></geometry>
          <material><ambient>0.08 0.08 0.08 1</ambient><diffuse>0.08 0.08 0.08 1</diffuse></material>
        </visual>
      </link>
    </model>
    <!-- East wall -->
    <model name="wall_east">
      <static>true</static>
      <pose>1.2192 0 0.1 0 0 1.5708</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>1.2192 0.025 0.2</size></box></geometry></collision>
        <visual name="vis">
          <geometry><box><size>1.2192 0.025 0.2</size></box></geometry>
          <material><ambient>0.08 0.08 0.08 1</ambient><diffuse>0.08 0.08 0.08 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- ===== ZONE DIVIDERS (1.5" white lines approximated as flat boxes) ===== -->
    <!-- Vertical divider: Area 1+2 (left) vs Area 3 (right) — at x=0 -->
    <model name="divider_lr">
      <static>true</static>
      <pose>0 0 0.006 0 0 0</pose>
      <link name="link">
        <visual name="vis">
          <geometry><box><size>0.038 1.2192 0.002</size></box></geometry>
          <material><ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse></material>
        </visual>
      </link>
    </model>
    <!-- Horizontal divider: Area 1 (bottom-left) vs Area 2 (top-left) — at y=0 -->
    <model name="divider_tb">
      <static>true</static>
      <pose>-0.6096 0 0.006 0 0 0</pose>
      <link name="link">
        <visual name="vis">
          <geometry><box><size>1.2192 0.038 0.002</size></box></geometry>
          <material><ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- ===== STARTING AREA (green, 12"x12" = 0.3048x0.3048, bottom-left corner) ===== -->
    <model name="start_area">
      <static>true</static>
      <!-- Bottom-left: x=-1.2192..(-0.9144), y=-0.6096..(-0.3048) -->
      <pose>-1.067 -0.4572 0.006 0 0 0</pose>
      <link name="link">
        <visual name="vis">
          <geometry><box><size>0.3048 0.3048 0.001</size></box></geometry>
          <material><ambient>0.0 0.6 0.0 1</ambient><diffuse>0.0 0.6 0.0 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- ===== LUNAR LANDING AREA (blue, top-left) ===== -->
    <model name="lunar_landing">
      <static>true</static>
      <pose>-0.9144 0.3048 0.006 0 0 0</pose>
      <link name="link">
        <visual name="vis">
          <geometry><box><size>0.5 0.4 0.001</size></box></geometry>
          <material><ambient>0.1 0.1 0.8 1</ambient><diffuse>0.1 0.1 0.8 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- ===== ANTENNA #1 — Area 2 (upper-left), faces south, BUTTON task ===== -->
    <model name="antenna1_base">
      <static>true</static>
      <pose>-0.8 0.35 0.0635 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>0.127 0.127 0.127</size></box></geometry></collision>
        <visual name="vis">
          <geometry><box><size>0.127 0.127 0.127</size></box></geometry>
          <material><ambient>0.05 0.05 0.05 1</ambient><diffuse>0.05 0.05 0.05 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- ===== ANTENNA #2 — Area 3 (right), faces south, CRANK task ===== -->
    <model name="antenna2_base">
      <static>true</static>
      <pose>0.5 -0.1 0.0635 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>0.127 0.127 0.127</size></box></geometry></collision>
        <visual name="vis">
          <geometry><box><size>0.127 0.127 0.127</size></box></geometry>
          <material><ambient>0.05 0.05 0.05 1</ambient><diffuse>0.05 0.05 0.05 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- ===== CRATER (Area 4) — 2ft diameter = 0.6096m, right-center ===== -->
    <!--  Approximated as a cylinder depression; LiDAR sees rim as obstacle ring  -->
    <model name="crater_rim">
      <static>true</static>
      <pose>0.7 0.15 0.04 0 0 0</pose>
      <link name="link">
        <collision name="col">
          <geometry><cylinder><radius>0.3048</radius><length>0.08</length></cylinder></geometry>
        </collision>
        <visual name="vis">
          <geometry><cylinder><radius>0.3048</radius><length>0.08</length></cylinder></geometry>
          <material><ambient>0.4 0.4 0.4 1</ambient><diffuse>0.4 0.4 0.4 1</diffuse></material>
        </visual>
      </link>
    </model>
    <!-- Crater inner flat bottom (8" diam = 0.2032m, lower) -->
    <model name="crater_floor">
      <static>true</static>
      <pose>0.7 0.15 -0.05 0 0 0</pose>
      <link name="link">
        <visual name="vis">
          <geometry><cylinder><radius>0.1016</radius><length>0.01</length></cylinder></geometry>
          <material><ambient>0.35 0.35 0.35 1</ambient><diffuse>0.35 0.35 0.35 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- ===== ANTENNA #3 — inside crater, faces west, PRESSURE PLATE / duck on top ===== -->
    <model name="antenna3_base">
      <static>true</static>
      <pose>0.7 0.15 -0.017 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>0.127 0.127 0.127</size></box></geometry></collision>
        <visual name="vis">
          <geometry><box><size>0.127 0.127 0.127</size></box></geometry>
          <material><ambient>0.05 0.05 0.05 1</ambient><diffuse>0.05 0.05 0.05 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- ===== ANTENNA #4 — Area 1 (lower-left), faces north, KEYPAD task ===== -->
    <model name="antenna4_base">
      <static>true</static>
      <pose>-0.8 -0.25 0.0635 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>0.127 0.127 0.127</size></box></geometry></collision>
        <visual name="vis">
          <geometry><box><size>0.127 0.127 0.127</size></box></geometry>
          <material><ambient>0.05 0.05 0.05 1</ambient><diffuse>0.05 0.05 0.05 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- ===== EXAMPLE ASTRO-DUCK SPAWN POINTS (5 of 6 random, 1 fixed on ant3) ===== -->
    <!-- These are representative; in practice ducks are physically placed randomly -->
    <!-- Duck on antenna #3 (fixed) — small cylinder placeholder -->
    <model name="duck_on_antenna3">
      <static>false</static>
      <pose>0.7 0.15 0.08 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><sphere><radius>0.04</radius></sphere></geometry></collision>
        <visual name="vis">
          <geometry><sphere><radius>0.04</radius></sphere></geometry>
          <material><ambient>1 0.9 0.0 1</ambient><diffuse>1 0.9 0.0 1</diffuse></material>
        </visual>
        <inertial><mass>0.05</mass></inertial>
      </link>
    </model>

  </world>
</sdf>
