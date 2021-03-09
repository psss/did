#!/bin/bash

cat <<EOT >> /usr/bin/own-program
#!/bin/bash
echo hello world
EOT

chmod a+x /usr/bin/own-program
