#if !defined __SYNTHLIB2_GRAMMAR_VISITOR_HPP
#define __SYNTHLIB2_GRAMMAR_VISITOR_HPP

#include "SynthLib2ParserFwd.hpp"
#include "SynthLib2ParserIFace.hpp"

namespace SynthLib2Parser {

  void Stam(int i);

    class GrammarVisitor : public ASTVisitorBase
    {
    private:
        u32 IndentLevel;
        inline string GetIndent();
        ostream& Out;
        SymbolTable* SymTbl;
        const SynthFunCmd* SynthFun;
        const FunDefCmd* FunDef;
        bool noGrmrRestrictions;

        GTerm* GrmrTerm; // the GTerm to match
        bool Matched; // whether it is successfully mathced
        u32 ExprSize; // size of the generated expression
        unordered_map<string, string> VarsBinding; // matching Grmr variables to Term variables

    public:
      GrammarVisitor(ostream& Out, GTerm* GrmrTerm, const SynthFunCmd* SynthFun, 
		     const FunDefCmd* FunDef, bool noGrmrRestrictions, SymbolTable* = NULL);
        virtual ~GrammarVisitor();

        bool  GetMatched();
        void  SetMatched(bool b);
        u32   GetExprSize();
        bool  AdheresToGrammar(const Term* TheTerm);
        const string Lookup(const string& GTermStr);
        bool  UnBind(const string& GTermStr);

        virtual void VisitProgram(const Program* Prog) override;

        virtual void VisitFunDefCmd(const FunDefCmd* Cmd) override;
        virtual void VisitFunDeclCmd(const FunDeclCmd* Cmd) override;
        virtual void VisitSynthFunCmd(const SynthFunCmd* Cmd) override;
        virtual void VisitSortDefCmd(const SortDefCmd* Cmd) override;
        virtual void VisitSetOptsCmd(const SetOptsCmd* Cmd) override;
        virtual void VisitVarDeclCmd(const VarDeclCmd* Cmd) override;
        virtual void VisitConstraintCmd(const ConstraintCmd* Cmd) override;
        virtual void VisitSetLogicCmd(const SetLogicCmd* Cmd) override;
        virtual void VisitCheckSynthCmd(const CheckSynthCmd* Cmd) override;
        virtual void VisitArgSortPair(const ArgSortPair* ASPair) override;

        virtual void VisitIntSortExpr(const IntSortExpr* Sort) override;
        virtual void VisitBVSortExpr(const BVSortExpr* Sort) override;
        virtual void VisitNamedSortExpr(const NamedSortExpr* Sort) override;
        virtual void VisitArraySortExpr(const ArraySortExpr* Sort) override;
        virtual void VisitRealSortExpr(const RealSortExpr* Sort) override;
        virtual void VisitFunSortExpr(const FunSortExpr* Sort) override;
        virtual void VisitBoolSortExpr(const BoolSortExpr* Sort) override;
        virtual void VisitEnumSortExpr(const EnumSortExpr* Sort) override;
        virtual void VisitStringSortExpr(const StringSortExpr* Sort) override;

        virtual void VisitLetBindingTerm(const LetBindingTerm* Binding) override;
        
        virtual void VisitFunTerm(const FunTerm* TheTerm) override;
        virtual void VisitLiteralTerm(const LiteralTerm* TheTerm) override;
        virtual void VisitSymbolTerm(const SymbolTerm* TheTerm) override;
        virtual void VisitLetTerm(const LetTerm* TheTerm) override;

        virtual void VisitLetBindingGTerm(const LetBindingGTerm* Binding) override;

        virtual void VisitFunGTerm(const FunGTerm* TheTerm) override;
        virtual void VisitLiteralGTerm(const LiteralGTerm* TheTerm) override;
        virtual void VisitSymbolGTerm(const SymbolGTerm* TheTerm) override;
        virtual void VisitLetGTerm(const LetGTerm* TheTerm) override;
        virtual void VisitConstantGTerm(const ConstantGTerm* TheTerm) override;
        virtual void VisitVariableGTerm(const VariableGTerm* TheTerm) override;

        virtual void VisitNTDef(const NTDef* Def) override;
        virtual void VisitLiteral(const Literal* TheLiteral) override;
    };

} /* end namespace */

#endif /* __SYNTHLIB2_GRAMMAR_VISITOR_HPP */

