import boto3.session
import pprint
#import common
import time
source_account = 'burstdev'
destination_account = 'default'
region = 'us-east-1'
# Should be set to rds or ec2
aws_service = 'rds'
#Provide a list of snapshots otherwise all will be moved
snapshots_to_move = ["burstdevdb-final-snapshot", "rhythmdev-final-snapshot"]
destination_tags = [
    {
        'Key': 'R1-Environment',
        'Value': 'prod'
    },
    {
        'Key': 'R1-Owners',
        'Value': 'sdeshpande@rhythmone.com'
    },
    {
        'Key': 'R1-Product',
        'Value': 'burstdev'
    },
    {
        'Key': 'R1-Role',
        'Value': 'account-consolidation-backup'
    }
]
#Don't modify
snapshot_rds_arns = {}
snapshot_ec2_names = {}
try:
    pp = pprint.PrettyPrinter(indent=4)
    source_aws = boto3.session.Session(profile_name=source_account, region_name=region)
    if destination_account == 'default':
        destination_aws = boto3.session.Session(region_name=region)
    else:
        destination_aws = boto3.session.Session(profile_name=destination_account, region_name=region)
    rds_client_source = source_aws.client('rds')
    ec2_client_source = source_aws.client('ec2')
    if len(snapshots_to_move) == 0:
        print("No snapshots in list to move, listing snapshots...")
        if aws_service == 'rds':
            rds_next_token = 'placeholder'
            while rds_next_token != '':
                rds_args = {'MaxRecords': 100}
                if rds_next_token != 'placeholder':
                    rds_args['Marker'] = rds_next_token
                rds_list = rds_client_source.describe_db_snapshots(**rds_args)
                rds_next_token = rds_list.get('Marker', '')
                for rds_snap in rds_list['DBSnapshots']:
                    snapshots_to_move.append(rds_snap['DBSnapshotIdentifier'])
                    snapshot_rds_arns[rds_snap['DBSnapshotIdentifier']] = rds_snap['DBSnapshotArn']
        else:
            ec2_next_token = 'placeholder'
            while ec2_next_token != '':
                ec2_args = {'MaxResults': 100, 'Filters': [{'Name': 'owner-id', 'Values': [source_aws.client('sts').get_caller_identity()['Account']]}]}
                if ec2_next_token != 'placeholder':
                    ec2_args['NextToken'] = ec2_next_token
                ec2_list = ec2_client_source.describe_snapshots(**ec2_args)
                ec2_next_token = ec2_list.get('NextToken', '')
                for ec2_snap in ec2_list['Snapshots']:
                    snapshots_to_move.append(ec2_snap['SnapshotId'])
                    for ec2_tag in ec2_snap.get('Tags', []):
                        if ec2_tag['Key'] == 'Name':
                            snapshot_ec2_names[ec2_snap['SnapshotId']] = ec2_tag['Value']
                            break
                    if snapshot_ec2_names.get(ec2_snap['SnapshotId']) is None:
                        snapshot_ec2_names[ec2_snap['SnapshotId']] = ''
    else:
        print("Retrieving additional info for requested copies.")
        if aws_service == 'rds':
            for snapshot_name in snapshots_to_move:
                snapshot_info = None
                snapshot_info = rds_client_source.describe_db_snapshots(DBSnapshotIdentifier=snapshot_name)['DBSnapshots']
                if len(snapshot_info) is None:
                    print("CAN'T COPY %s! Can't detect ARN." % snapshot_name)
                    continue
                snapshot_rds_arns[snapshot_name] = snapshot_info[0]['DBSnapshotArn']
                print("Got ARN for %s (%s)" % (snapshot_name, snapshot_info[0]['DBSnapshotArn']))
        else:
            for snapshot_name in snapshots_to_move:
                snapshot_info = None
                snapshot_info = ec2_client_source.describe_snapshots(SnapshotIDs=[snapshot_name])['Snapshots']
                if len(snapshot_info) > 0:
                    for ec2_tag in snapshot_info[0].get('Tags', []):
                        if ec2_tag['Key'] == 'Name':
                            snapshot_ec2_names[snapshot_name] = ec2_tag['Value']
                            print("Got Name for %s (%s)" % (snapshot_name, ec2_tag['Value']))
                            break
                if snapshot_ec2_names.get(snapshot_name) is None:
                    snapshot_ec2_names[snapshot_name] = ''
    if len(snapshots_to_move) == 0:
        print("Still couldn't find any snapshots, aborting.")
        exit()
    print("Got %d snapshots to work on." % len(snapshots_to_move))
    print(snapshots_to_move)
    # Allow destination account access to all snapshots
    for snap_id in snapshots_to_move:
        print("Modifying %s to give destination account access" % snap_id)
        if aws_service == 'rds':
            rds_client_source.modify_db_snapshot_attribute(
                DBSnapshotIdentifier=snap_id,
                AttributeName='restore',
                ValuesToAdd=[destination_aws.client('sts').get_caller_identity()['Account']]
            )
        else:
            ec2_client_source.modify_snapshot_attribute(
                Attribute='createVolumePermission',
                OperationType='add',
                SnapshotId=snap_id,
                UserIds=[destination_aws.client('sts').get_caller_identity()['Account']]
            )
    print("Waiting for 60 seconds for changes to propagate")
    time.sleep(60)
    # Start trying to copy the snapshots
    # RDS snapshot name is DBSnapshotIdentifier whereas EBS snapshot is "Name" tag
    if aws_service == 'rds':
        rds_client_dest = destination_aws.client('rds')
        for snap_id in snapshots_to_move:
            print("Initiating copy on %s" % snap_id)
            rds_tags = destination_tags
            new_snapshot = rds_client_dest.copy_db_snapshot(
                SourceDBSnapshotIdentifier=snapshot_rds_arns[snap_id],
                TargetDBSnapshotIdentifier=source_account.upper() + '-' + snap_id,
                Tags=destination_tags + [{'Key': 'Snapshot-Source', 'Value': snapshot_rds_arns[snap_id]}]
            )
            if new_snapshot.get('DBSnapshot', {}).get('DBSnapshotIdentifier') is None:
                print(new_snapshot)
            else:
                print("New copy is %s" % new_snapshot.get('DBSnapshot', {}).get('DBSnapshotIdentifier'))
    else:
        existing_ec2_snaps = []
        ec2_client_dest = destination_aws.client('ec2')
        # Check for dupes first
        ec2_next_token = 'placeholder'
        while ec2_next_token != '':
            ec2_args = {
                'MaxResults': 100,
                'Filters': [
                    {
                        'Name': 'owner-id',
                        'Values': [destination_aws.client('sts').get_caller_identity()['Account']]
                    },
                    {
                        'Name': 'tag-key',
                        'Values': ['Snapshot-Source']
                    }
                ]
            }
            if ec2_next_token != 'placeholder':
                ec2_args['NextToken'] = ec2_next_token
            ec2_list = ec2_client_dest.describe_snapshots(**ec2_args)
            ec2_next_token = ec2_list.get('NextToken', '')
            for ec2_snap in ec2_list['Snapshots']:
                for ec2_tag in ec2_snap.get('Tags', []):
                    if ec2_tag['Key'] == 'Snapshot-Source':
                        existing_ec2_snaps.append(ec2_tag['Value'])
                        break
        for snap_id in snapshots_to_move:
            new_name_tag = source_account.upper() + '-'
            if len(snapshot_ec2_names[snap_id]) == 0:
                new_name_tag += snap_id
            else:
                new_name_tag += snapshot_ec2_names[snap_id]
            if snap_id in existing_ec2_snaps:
                print("Skipping %s as it looks like we already have a copy of that..." % snap_id)
                continue
            print("Initiating copy on %s" % snap_id)
            new_snapshot = ec2_client_dest.copy_snapshot(
                SourceSnapshotId=snap_id,
                Description=source_account.upper() + '-' + snap_id
            )
            print("New copy is %s" % new_snapshot['SnapshotId'])
            print("Tagging copy %s of ID %s" % (new_snapshot['SnapshotId'], snap_id))
            ec2_client_dest.create_tags(
                Resources=[new_snapshot['SnapshotId']],
                Tags=destination_tags + [{'Key': 'Name', 'Value': new_name_tag}, {'Key': 'Snapshot-Source', 'Value': snap_id}]
            )
    print("All done.")
except Exception as e:
    print(str(e))
