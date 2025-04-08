echo 'Installing packages'

amazon-linux-extras enable postgresql16
yum clean metadata
yum install postgresql16-devel
