cmake_minimum_required(VERSION 2.8.3)
project(my_catkin_package)

find_package(catkin REQUIRED COMPONENTS)

catkin_python_setup()

catkin_package()

include_directories(
  ${catkin_INCLUDE_DIRS}
)
