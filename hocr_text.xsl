<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xhtml="http://www.w3.org/1999/xhtml"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    version="2.0">
    <xsl:output method="text" omit-xml-declaration="yes" indent="no"/>

    <xsl:param name="x0"/>
    <xsl:param name="y0"/>
    <xsl:param name="x1"/>
    <xsl:param name="y1"/>

    <xsl:variable name="r0" select="xs:integer($x0)"/>
    <xsl:variable name="r1" select="xs:integer($y0)"/>
    <xsl:variable name="r2" select="xs:integer($x1)"/>
    <xsl:variable name="r3" select="xs:integer($y1)"/>

    <xsl:template match="text()"/>

    <xsl:template match="/">
        <xsl:apply-templates select="//xhtml:span"/>
    </xsl:template>

    <xsl:template match="xhtml:span[@class='ocr_line' or @class='ocr_textfloat']">
        <xsl:for-each select="./xhtml:span[@class='ocrx_word']">
             <xsl:variable name="tokens" select="for $x in tokenize(@title, '\s+') return $x"/>
             <xsl:variable name="b0" select="xs:integer($tokens[2])"/>
             <xsl:variable name="b1" select="xs:integer($tokens[3])"/>
             <xsl:variable name="b2" select="xs:integer($tokens[4])"/>
             <xsl:variable name="b3" select="xs:integer(substring-before($tokens[5],';'))"/>
             <!-- is value in range -->
             <xsl:if test="$b0 &gt;= $r0 and $b1 &gt;= $r1 and $b2 &lt;= $r2 and $b3 &lt;= $r3">
                 <xsl:value-of select="."/>
                 <!-- simplistic spacing, assumes lines will fall within regions -->
                 <xsl:choose>
                 <xsl:when test="position()=last()">
                      <!-- line return -->
                      <xsl:text>&#xA;</xsl:text>
                 </xsl:when>
                 <xsl:otherwise>
                      <!-- add space -->
                      <xsl:text> </xsl:text>
                 </xsl:otherwise>
                 </xsl:choose>
             </xsl:if>
        </xsl:for-each>
    </xsl:template>
</xsl:stylesheet>
