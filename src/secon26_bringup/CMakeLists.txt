cmake_minimum_required(VERSION 3.8)
project(secon26_bringup)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS scripts/tb6612_driver.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME tb6612_driver)

install(PROGRAMS scripts/mpu9250_driver.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME mpu9250_driver)

install(PROGRAMS scripts/dsservo_driver.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME dsservo_driver)

install(PROGRAMS scripts/simple_navigator.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME simple_navigator)

install(PROGRAMS secon26_mission_controller.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME secon26_mission_controller)

install(DIRECTORY launch config urdf worlds maps
  DESTINATION share/${PROJECT_NAME})

ament_package()
