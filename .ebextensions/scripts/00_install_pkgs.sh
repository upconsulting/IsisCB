echo 'Installing packages'

amazon-linux-extras enable postgresql11
yum clean metadata
yum install postgresql11-devel
