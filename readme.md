Import commands
Both LMS26 and LMS27 share these SG IDs from the ec2-imported module:

sg-038da1678593d805c — appears on nearly all instances, likely already managed (base SG)
sg-0b9cf8c879a27a8f1 — shared by LMS26 and LMS27
sg-0e49ce0845df088e9 — shared by LMS26 and LMS27
Since both instances share the same pair, assign one per instance. Run these import commands before terragrunt apply, from inside the aws-sg module directory:


# Import sg-0b9cf8c879a27a8f1 as USAWA2PAPLMS26's SG
terragrunt import 'module.security_groups["USAWA2PAPLMS26"].aws_security_group.this[0]' sg-0b9cf8c879a27a8f1

# Import sg-0e49ce0845df088e9 as USAWA2PAPLMS27's SG
terragrunt import 'module.security_groups["USAWA2PAPLMS27"].aws_security_group.this[0]' sg-0e49ce0845df088e9
