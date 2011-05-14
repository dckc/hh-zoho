<xsl:transform
  version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:s="http://www.w3.org/2000/01/rdf-schema#"
  xmlns:dt="http://www.w3.org/2001/XMLSchema#"
  xmlns:owl="http://www.w3.org/2002/07/owl#"
  >


  <xsl:output method="text" />

  <xsl:variable name="Int"
		select='"http://www.w3.org/2001/XMLSchema#integer"'/>

  <xsl:template match="owl:Class">
    <xsl:variable name="tName" select='@r:ID' />

    <xsl:text>CREATE TABLE </xsl:text>
    <xsl:value-of select='$tName' />
    <xsl:text> (&#x0A;</xsl:text>

    <xsl:for-each select="s:subClassOf/owl:Restriction">
      <xsl:if test='position() &gt; 1'>
	<xsl:text> , </xsl:text>
      </xsl:if>

      <xsl:variable name="fieldElt" select='owl:onProperty/*' />
      <xsl:variable
       name="fName"
       select='substring-after($fieldElt/@r:about, "#")' />

      <xsl:variable
       name="fRef"
       select='substring-after(owl:allValuesFrom/@r:resource, "#")' />

      <xsl:variable
       name="fType"
       select='substring-after($fieldElt/s:range/@r:resource, "#")' />
      
      <xsl:text>  </xsl:text>
      <xsl:value-of select='$fName' />

      <xsl:choose>
	<xsl:when test='$fRef'>
	  <xsl:text> INTEGER</xsl:text>
	  <!-- foreign key? @@ -->
	</xsl:when>

	<xsl:when test='$fName = "id"'> <!-- KLUDGE@@ -->
	  <xsl:text> INTEGER PRIMARY KEY</xsl:text>
	</xsl:when>

	<xsl:when test='$fType = "integer"'>
	  <xsl:text> INTEGER</xsl:text>
	</xsl:when>

	<xsl:when test='$fType = "string"'>
	  <xsl:text> TEXT</xsl:text>
	</xsl:when>

	<xsl:when test='$fType = "float"'>
	  <xsl:text> FLOAT</xsl:text>
	</xsl:when>

	<xsl:when test='$fType = "date"'>
	  <xsl:text> DATE</xsl:text>
	</xsl:when>

	<xsl:when test='$fType = "decimal"'>
	  <xsl:text> NUMBER</xsl:text>
	</xsl:when>

	<xsl:otherwise>
	  <xsl:message>
	    @@unknown type: <xsl:value-of select='$fType'/>
	  </xsl:message>
	</xsl:otherwise>
      </xsl:choose>
      <xsl:text> &#x0A;</xsl:text>

    </xsl:for-each>
    <xsl:text> );&#x0A;</xsl:text>
  </xsl:template>

  <!-- don't pass text thru -->
  <xsl:template match="text()|@*">
  </xsl:template>

</xsl:transform>
