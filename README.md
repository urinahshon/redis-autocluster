# Redis Autocluster
With this project you can create Redis AMI (with Ansible) on AWS
And deploy Redis instances on AWS (with Terraform)
The first node will be Redis master and the rest of them will be slaves
The autocluster work with Python
And on the Redis image also have Twemproxy and Redis Sentinel

To use the AWS autocluster features, you will need an IAM policy that allows the
plugin to discover the node list. The following is an example of such a policy:

.. code-block:: json

  {
      "Version": "2012-10-17",
      "Statement": [
          {
              "Effect": "Allow",
              "Action": [
                  "autoscaling:DescribeAutoScalingInstances",
                  "ec2:DescribeInstances"
              ],
              "Resource": [
                  "*"
              ]
          }
      ]
  }

If you do not want to use the IAM role for the instances, you could create a role
and specify the ``AWS_ACCESS_KEY_ID`` and ``AWS_SECRET_ACCESS_KEY``.