import boto3
import json
import paramiko
import time

def lambda_handler(event, context):


    print("InstallWantedApplications v1") 

    s3_client = boto3.client('s3')
    ec2_client = boto3.client('ec2')

    print("Clientes importados correctamente")

    s3_client.download_file('my-key-bucket-rodri','ubuntu-key.pem', '/tmp/ubuntu-key.pem')
    s3_client.download_file('my-key-bucket-rodri','WantedApplications.json', '/tmp/WantedApplications.json')

    f = open('/tmp/WantedApplications.json')
    contents = f.read()
    s3_content = json.loads(contents)

    whitelistedApps = s3_content["WhitelistedApps"]
    instanceId = s3_content["InstanceId"]

    print("Clave descargada correctamente")

    k = paramiko.RSAKey.from_private_key_file("/tmp/ubuntu-key.pem")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print("Paramiko usado correctamente")

    instances = ec2_client.describe_instances(
        InstanceIds=[
            instanceId
        ]
    )

    if instances["Reservations"][0]["Instances"][0]["State"]["Name"] == "running":
        host = instances["Reservations"][0]["Instances"][0]["PublicIpAddress"]
    else:
        print("Instance is not running")
        return {
            'statusCode': 200,
            'body': json.dumps('Instance is not running')
        }
    
    print("Connecting to " + host)
    c.connect( hostname = host, username = "ubuntu", pkey = k )
    print("Connected to " + host)

    print("Executing {}".format("apt list --installed"))
    stdin , stdout, stderr = c.exec_command("apt list --installed")

    packages = str(stdout.read(), 'utf-8')
    installed = packages.replace("Listing...", "", 1)
    installed_list = installed.splitlines()
    installed_list.pop(0)

    installed_packages = [] 

    for i in installed_list:
        package = i.split("/")[0]
        installed_packages.append(package)

    ssh_transp = c.get_transport()

    for w in whitelistedApps:
        if w not in installed_packages:
            command = "sudo apt -y install " + w
            print("Executing {}".format(command))
            chan = ssh_transp.open_session()
            chan.setblocking(0)
            chan.exec_command(command)
            
            counter = 0

            while not chan.exit_status_ready():
                time.sleep(1)
                counter += 1
                if counter >= 180:
                    break

    return {
            'statusCode': 200,
            'body': json.dumps('Hello from Lambda!')
    }
    

    
