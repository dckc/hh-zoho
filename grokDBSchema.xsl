<xsl:transform
  version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:h="http://www.w3.org/1999/xhtml"
  xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:s="http://www.w3.org/2000/01/rdf-schema#"
  xmlns:dt="http://www.w3.org/2001/XMLSchema#"
  xmlns:owl="http://www.w3.org/2002/07/owl#"
  >


  <xsl:output method="xml" indent="yes"/>

  <xsl:variable name="Int"
		select='"http://www.w3.org/2001/XMLSchema#integer"'/>

  <xsl:variable name="String"
		select='"http://www.w3.org/2001/XMLSchema#string"'/>

  <xsl:variable name="Float"
		select='"http://www.w3.org/2001/XMLSchema#float"'/>

  <xsl:variable name="Date"
		select='"http://www.w3.org/2001/XMLSchema#date"'/>

  <xsl:variable name="Decimal"
		select='"http://www.w3.org/2001/XMLSchema#decimal"'/>


  <xsl:template match="/">
    <r:RDF>
      <xsl:apply-templates />
    </r:RDF>
  </xsl:template>

  <xsl:template match="h:table"> <!-- special class? -->

    <xsl:for-each select="h:tbody[h:tr/h:td]">
      <xsl:variable name="tName" select="normalize-space(h:tr[1]/h:td[1])"/>

      <owl:Class r:ID='{$tName}'>
	<s:label><xsl:value-of select='$tName'/></s:label>

	<xsl:for-each select='h:tr'>
	  <xsl:variable name="fName" select="normalize-space(h:td[2])"/>
	  <xsl:variable name="fType" select="normalize-space(h:td[3])"/>
	  <xsl:variable name="fRef" select="normalize-space(h:td[4])"/>
	  <xsl:variable name="fDesc" select="h:td[5]"/>

	  <xsl:choose>
	    <xsl:when test='$fRef'>
	      <s:subClassOf>
		<owl:Restriction>
		  <owl:onProperty>
		    <owl:ObjectProperty r:about='#{$fName}'>
		      <s:comment><xsl:value-of select='$fDesc'/></s:comment>
		    </owl:ObjectProperty>
		  </owl:onProperty>
		  <owl:allValuesFrom r:resource='#{$fRef}'/>
		</owl:Restriction>
	      </s:subClassOf>
	    </xsl:when>

	    <xsl:otherwise>
	      <s:subClassOf>
		<owl:Restriction>
		  <owl:onProperty>
		    <owl:DataTypeProperty r:about='#{$fName}'>
		      <xsl:choose>
			<xsl:when test='$fType = "int"'>
			  <s:range r:resource="{$Int}" />
			</xsl:when>
			<xsl:when test='$fType = "text"'>
			  <s:range r:resource="{$String}" />
			</xsl:when>
			<xsl:when test='$fType = "float"'>
			  <s:range r:resource="{$Float}" />
			</xsl:when>
			<xsl:when test='$fType = "date"'>
			  <s:range r:resource="{$Date}" />
			</xsl:when>
			<xsl:when test='$fType = "decimal"'>
			  <s:range r:resource="{$Decimal}" />
			</xsl:when>
			<xsl:otherwise>
			  <xsl:message>
			    @@unknown type: <xsl:value-of select='$fType'/>
			  </xsl:message>
			</xsl:otherwise>
		      </xsl:choose>
		      <s:comment><xsl:value-of select='$fDesc'/></s:comment>
		    </owl:DataTypeProperty>
		  </owl:onProperty>
		  <owl:cardinality
		   r:datatype='{$Int}'>1</owl:cardinality>
		</owl:Restriction>
	      </s:subClassOf>
	    </xsl:otherwise>
	  </xsl:choose>
	</xsl:for-each>
      </owl:Class>
    </xsl:for-each>
  </xsl:template>

  <!-- don't pass text thru -->
  <xsl:template match="text()|@*">
  </xsl:template>

</xsl:transform>
