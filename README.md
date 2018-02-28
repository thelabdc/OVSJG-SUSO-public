# OVSJG-SUSO

Analyses and automation related to the OVSJG SUSO project.

## Automation

Much of this repository is dedicated to the automation of the letter sending process.
In order to get that going, run

```
pip install -e .
```

You will then find the command `susocli` on your path. That command requires a config
file, a template of which can be found in `config.template.yml`. You'll need to fill that
out.

The automation aspect of this is handled by the `Dockerfile`. This is run on a the
ktensor box (10.56.6.64) as the following cron job:

```
0 19-23 * * 1-5 docker run --rm -v /mnt/dockervols/suso:/work thelabdc/ovsjg-suso susocli run /suso/config.yml -t /work/tex -p /work/pdf >> /mnt/dockervols/suso/log 2>&1
1 0 * * 2-6 docker run --rm -v /mnt/dockervols/suso:/work thelabdc/ovsjg-suso susocli run /suso/config.yml -t /work/tex -p /work/pdf >> /mnt/dockervols/suso/log 2>&1
31 0 * * 2-6 docker run --rm -v /mnt/dockervols/suso:/work thelabdc/ovsjg-suso susocli run /suso/config.yml -t /work/tex -p /work/pdf >> /mnt/dockervols/suso/log 2>&1
```

Though note that the first time you run `susocli` you'll need to have run `susocli create` to create the relevant database tables.

## Other documentation

[OSF](https://osf.io/7jdr4/): Our project page on OSF.
