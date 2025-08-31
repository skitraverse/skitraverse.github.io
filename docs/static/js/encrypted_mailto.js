// Email obfuscator script 2.1 by Tim Williams, University of Arizona
// Random encryption key feature coded by Andrew Moulden
// This code is freeware provided these four comment lines remain intact
// A wizard to generate this code is at http://www.jottings.com/obfuscator/
(function encrypted_email() {
    {
        coded = "zSwy3.Z.v3tk@mBywT.NvB"
        key = "mVtvcY1pASa7lGnIKfQ94dBUJqNuR2jXyHTb3iDFgOeoW8Cxhr5EZMk6Lz0wsP"
        shift=coded.length
        link=""
        for (i=0; i<coded.length; i++) {
            if (key.indexOf(coded.charAt(i))==-1) {
                ltr = coded.charAt(i)
                link += (ltr)
            }
            else {     
                ltr = (key.indexOf(coded.charAt(i))-shift+key.length) % key.length
                link += (key.charAt(ltr))
            }
        }
        document.write("<a href='mailto:"+link+"'>Contact</a>")
    }
}).call(this);
