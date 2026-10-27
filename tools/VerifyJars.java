import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.Enumeration;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;

/** Loads (without initializing) every class of the given jars to detect ClassFormatErrors. */
public class VerifyJars {
    public static void main(String[] args) throws Exception {
        URL[] urls = new URL[args.length - 1];
        for (int i = 1; i < args.length; i++) urls[i - 1] = new File(args[i]).toURI().toURL();
        URLClassLoader cl = new URLClassLoader(urls, null);
        int ok = 0, fmt = 0, other = 0;
        JarFile jf = new JarFile(args[0]);
        Enumeration en = jf.entries();
        while (en.hasMoreElements()) {
            String n = ((JarEntry) en.nextElement()).getName();
            if (!n.endsWith(".class")) continue;
            String cn = n.substring(0, n.length() - 6).replace('/', '.');
            try {
                Class.forName(cn, false, cl);
                ok++;
            } catch (ClassFormatError e) {
                fmt++;
                System.out.println("FORMAT " + cn + ": " + e);
            } catch (Throwable e) {
                other++;
            }
        }
        System.out.println(args[0] + " loaded=" + ok + " formatErrors=" + fmt + " otherLinkIssues=" + other);
    }
}
