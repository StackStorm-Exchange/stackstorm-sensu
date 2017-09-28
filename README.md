# Sensu Integration Pack

Integrates with [Sensu](http://sensuapp.org/) monitoring framework.

## WARNING
This pack has had a major rewrite as of version 0.3.0. The local-script runners have been replaced
with Python runners. Some broken actions have been removed. Some output has changed.
If you are using Sensu actions, please check your workflows & rules.

### Prerequisites
Sensu and StackStorm, up and running. See installation for [Sensu](http://sensuapp.org/docs/latest/installation/) and [StackStorm](http://docs.stackstorm.com/install).

## Setup
### Install Sensu pack on StackStorm

1. Install the [Sensu pack](https://github.com/StackStorm-Exchange/stackstorm-sensu):

    ```
    # Install sensu
    st2 pack install sensu

    # Check it:
    st2 action list --pack=sensu
    ```

2. Copy the example configuration in [sensu.yaml.example](./sensu.yaml.example)
to `/opt/stackstorm/configs/sensu.yaml` and edit as required. It must contain:

* ``host`` - Host where Sensu API endpoint is running
* ``port`` - Sensu API port (default 4567)
* ``user`` - Sensu integration user
* ``pass`` - Sensu integration password
* ``ssl`` - Whether to verify the Sensu SSL certificate or not

**Note** : When modifying the configuration in `/opt/stackstorm/configs/` please
           remember to tell StackStorm to load these new values by running
           `st2ctl reload --register-configs`

3. Check that the actions work:

    ```
    st2 run sensu.check_list
    ```

### Configure Sensu to send events to StackStorm

There is a [Sensu Plugins for the StackStorm](https://github.com/sensu-plugins/sensu-plugins-stackstorm). This plugin has a [Sensu Event Handler](https://sensuapp.org/docs/latest/reference/handlers.html) which is named `st2_handler.rb`, it sends all **relevant** events to StackStorm. Use Sensu configuration to define **relevant** events.

On StackStorm side, Sensu events will fire a Sensu trigger on each received event. The `sensu.event_handler` trigger type is auto-registered by the handler; you can run the `st2_handler.rb` manually to get the trigger created. Once created, you can see the [trigger](http://docs.stackstorm.com/rules.html#trigger) with `st2 trigger list --pack=sensu`. It now can be used in StackStorm [Rules](http://docs.stackstorm.com/rules.html) to define what actions to take on which events, based on supplied criteria.

Here are step-by-step instructions:

1. Install the Sensu StackStorm Plugin by the `sensu-install` command

    ```
    sudo sensu-install -p stackstorm
    ```

2. Set up StackStorm endpoints and credentials according to [this document](https://github.com/sensu-plugins/sensu-plugins-stackstorm#configuration).

3. Note that handler invocation auto-creates Sensu trigger type on StackStorm side. Ensure that the Sensu trigger is created on StackStorm:

    ```
    st2 trigger list --pack=sensu
    ```

4. Create and configure Sensu StackStorm handler - call it `st2` - for sending Sensu events to StackStorm:

    ```json
    cat /etc/sensu/conf.d/handler_st2.json
    {
      "handlers": {
        "st2": {
          "type": "pipe",
          "command": "/opt/sensu/embedded/bin/st2_handler.rb"
        }
      }
    }
    ```

5. Add `st2` handler to `handlers` field of desired sensu checks to route events to StackStorm. Here is how to add st2 handler to Sensu memory check:

    ```json
    cat /etc/sensu/conf.d/check_memory.json
    {
      "checks": {
        "memory": {
          "command": "/etc/sensu/plugins/check-memory.sh -w 128 -c 64",
          "interval": 10,
          "subscribers": [
            "test"
          ],
          "handlers": ["default", "st2"]
        }
      }
    }
    ```
    With this config, the memory events from this check will be sent to StackStorm.

    Refer to [Sensu documentation](http://sensuapp.org/docs/latest/guide) for details on how to configure handlers and checks.

6. Profit. At this point, StackStorm will receive sensu events and fire sensu triggers. Use them in Rules to fire an action, or a workflow of actions, on Sensu event.

### Handler options

1. The handler supports unauthed st2 endpoints (server side authentication turned off). Though
   this is not recommended, you can use this for local testing.

   ```
   echo '{"client": {"name": 1}, "check":{"name": 2}, "id": "12345"}' | /opt/sensu/embedded/bin/st2_handler.rb --unauthed
   ```
2. The handler also supports turning on/off ssl verification for all API requests to st2. By
   default, SSL verification is turned off as evaluation versions of st2 ship with self-signed
   certs. To turn on ssl verify, use ```--ssl-verify``` option.

   ```
   echo '{"client": {"name": 1}, "check":{"name": 2}, "id": "12345"}' | /opt/sensu/embedded/bin/st2_handler.rb --ssl-verify
   ```

3. If for whatever reason, you've to debug the handler, you can use the --verbose option.

   ```
   echo '{"client": {"name": 1}, "check":{"name": 2}, "id": "12345"}' | /opt/sensu/embedded/bin/st2_handler.rb --verbose
   ```

### Example
Let's take monitoring StackStorm itself for end-to-end example. Sensu will watch for StackStorm action runners, `st2actionrunners`, fire an event when it's less then 10. StackStorm will catch the event and trigger an action. A simple action that dumps the event payload to the file will suffice as example; in production the action will be a troubleshooting or remediation workflow.

Before proceeding further, please ensure you have the latest version of Ruby installed.

1. If Sensu `check_process.rb` check plugin is not yet installed, install it now (look up Sensu [docs here](http://sensu-plugins.io/docs/installation_instructions.html) for more details):

    ```
    sudo gem install sensu-plugins-process-checks
    ```

Test to ensure `check-process.rb` is working as expected. Assuming there are two currently executing st2actionrunner processes, you should see the following
output:

    ```
    root@2e1d15fd5d07:/# check-process.rb -p st2actionrunner -c 2
    CheckProcess OK: Found 2 matching processes; cmd /st2actionrunner/
    root@2e1d15fd5d07:/# check-process.rb -p st2actionrunner -c 1
    CheckProcess CRITICAL: Found 2 matching processes; cmd /st2actionrunner/
    ```

2. Create a Sensu check json like below. This check watches for keeping StackStorm action runners count at 10, and fires an event if the number of runners is less than 10. Note that is using `st2` handler.

    ```json
    cat /etc/sensu/conf.d/check_st2actionrunner.json
    {
      "checks": {
        "st2actionrunner_check": {
          "handlers": ["default", "st2"],
          "command": "/etc/sensu/plugins/check-process.rb -p st2actionrunner -C 2 ",
          "interval": 60,
          "subscribers": [ "test" ]
        }
      }
    }
    ```
    Make sure the client is configured to get this check via `test` subscription.

    ```json
    cat /etc/sensu/conf.d/client.json
    {
      "client": {
        "name": "test",
        "address": "localhost",
        "subscriptions": [ "test" ]
      }
    }
    ```
    Restart Sensu server and client to pick up the changes:

    ```
    sudo service sensu-server restart
    sudo service sensu-client restart
    ```
    At this point sensu should be running.

3. Now back to StackStorm. Create StackStorm rule definition (This sample is a part of the pack, [`rules/sample.on_action_runner_check.yaml`](rules/sample.on_action_runner_check.yaml)):

    ```yaml
    cat /opt/stackstorm/packs/sensu/rules/sample.on_action_runner_check
    ---
      name: sample.on_action_runner_check
      description: Sample rule that dogfoods st2.
      pack: sensu
      trigger:
        type: sensu.event_handler
      criteria:
        trigger.check.name:
          pattern: "st2actionrunner_check"
          type: "equals"
        trigger.check.output:
          pattern: "CheckProcess CRITICAL*"
          type: "matchregex"
      action:
        ref: "core.local"
        parameters:
          cmd: "echo \"{{trigger}}\" >> /tmp/sensu-sample.out"
      enabled: true
    ```

    and load the rule:

    ```
    cd /opt/stackstorm/packs/sensu
    st2 rule create rules/sample.on_action_runner_check.yaml
    ```
    StackStorm is now waiting for Sensu event.

4. Fire it up: create a Sensu event by Starting an st2actionrunner process.

    ```
    ps auxww | grep st2actionrunner
    sudo service st2actionrunner stop
    ```
    Wait for sensu event to be triggered - check [Uchiwa](https://github.com/sensu/uchiwa) if you have it, or watch the log:
    ```
    tail -f /var/log/sensu/sensu-server.log | grep --line-buffered st2actionrunner
    ```

    Watch the action triggered in StackStorm: `st2 execution list`.  and verify the result by ckecking the file created by the action:

    You can also see that the rule triggered an action in StackStorm UI, under History tab.

5. In this simple example, StackStorm just dumped the content of the check output to the file. In a real auto-remediation, a workflow of actions will get StackStorm runners back to normal. For now, just do that manually:

    ```
    st2ctl restart
    ```

Enjoy StackStorm with Sensu!
