from setuptools import setup

package_name = 'gamepad_controller'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_cmake_core/cmake/package_templates',
         ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    author='Robot Team',
    author_email='robot@example.com',
    maintainer='Robot Team',
    maintainer_email='robot@example.com',
    url='https://github.com/Eroros/uofm-competition-bot',
    description='Gamepad controller for remote robot drive',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'gamepad_controller = gamepad_controller.gamepad_controller_node:main',
        ],
    },
)
