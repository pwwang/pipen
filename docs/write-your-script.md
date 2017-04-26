# Write your script
<!-- toc -->

## Choose your language
You can either specify the path of interpreter to `p.lang` or `p.defaultSh`, if the interpreter is in `$PATH`, you can directly give the basename of the interpreter.  
For example, if you have your own perl installed at `/home/user/bin/perl`, then you need to tell `pyppl` where it is: `p.lang = "/home/user/bin/perl"`. If `/home/user/bin` is in your `$PATH`, you can simply do: `p.lang = "perl"`  
You can also use [shebang][1] to specify the interperter:
```perl
#!/home/usr/bin/perl
# You perl code goes here
```
Theoretically, `pyppl` supports any language.

## Use placeholders
You can use all available placeholders in the script. Each job will have its own script. See [here](https://pwwang.gitbooks.io/pyppl/content/placeholders.html) for details of placeholders.

## Use a template
You can also put the script into a file, and use it with a `template:` prefix: `p.script = "template:/a/b/c.pl"`  
You may also use the placeholders in the template, where everything should be the same when you put the script directly to `p.script`.

## Debug your script
If you need to debug your script, you just need to find the real running script, which is at: `<workdir>/scripts/script.<index>`. All the placeholders in the script have been replaced with actual values. You can debug it using the tool according to the language you used for the script.

[1]: https://en.wikipedia.org/wiki/Shebang_(Unix)
