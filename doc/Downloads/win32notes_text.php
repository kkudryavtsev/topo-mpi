<!--CB: should be able to remove this when windows version includes a shell-->

<H3><A NAME="unix-commands-on-win">Translating UNIX commands to Windows</A></H3>

<P>The Windows equivalent of 'the shell' is its 'Command Prompt'. The
easiest way to start this is by clicking on 'Start', then 'Run', then
typing <code>cmd</code>, then clicking 'Ok'.

<P>To convert UNIX shell commands to Windows Command Prompt commands:
<ul>
<li>Replace <code>~</code> in a path with the path to your <code>My Documents</code> folder
(e.g. <code>~/topographica</code> might become <code>"%HOMEPATH%\My Documents\topographica"</code>)</li>
<li>Replace any forward slash '<code>/</code>' in a path with a backslash '<code>\</code>'</li>
<li>Single quotes (<code>'</code>) must appear inside double quotes
(<code>"</code>); double quotes cannot appear inside single quotes 
<li>Filenames on Windows usually need double quotes, because the
paths typically contain spaces (e.g. "My Documents" or "Program Files")
<li>Unix commands such as <code>cp</code> usually have equivalents
(<code>copy</code> in this case); see one of the references on the
web, e.g. <A
HREF="http://www.yolinux.com/TUTORIALS/unix_for_dos_users.html">UNIX
for DOS Users</A></li>
</ul>

<P>
Example UNIX command:
<BR><code>topographica -g ~/topographica/examples/lissom_oo_or.ty</code>
<BR>
Windows equivalent:
<BR><code>topographica -g "%HOMEPATH%\My Documents\topographica\examples\lissom_oo_or.ty"</code>



